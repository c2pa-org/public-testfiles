//! Sign, damage and read the test files in `2.4` and `2.5`.
//!
//! Usage:
//!   make_testfile create <source> <dest> <description>
//!   make_testfile edit <source> <parent> <dest> <description> [<component>...]
//!   make_testfile embed <store-from> <into> <dest> [sig | uri <text>]
//!   make_testfile read <asset> <out-dir>
//!
//! `create` signs a newly synthesised asset (`c2pa.created`, algorithmicMedia).
//! `edit` signs an edited asset with `parent` as its parentOf ingredient and
//! each `component` as a componentOf ingredient (`c2pa.opened`, `c2pa.edited`,
//! and one `c2pa.placed` per component).
//! `embed` copies the C2PA Manifest Store of `store-from` into `into`
//! unchanged, or after flipping the last byte of the active manifest's
//! signature (`sig`), or after changing the case of the first letter of the
//! last occurrence of `text` (`uri`).
//! `read` writes `manifest_store.json` and `detailed.json` for an asset.
//!
//! Assets are signed with the c2pa-rs ES256 test certificate
//! (`sdk/tests/fixtures/certs/es256.pub`), set by `C2PA_CERTS`, and are
//! read with that directory's `trust/test_cert_root_bundle.pem` as the
//! trust list.

use std::{
    fs::File,
    path::{Path, PathBuf},
};

use anyhow::{bail, ensure, Context as _, Result};
use c2pa::{
    create_signer,
    jumbf_io::{load_jumbf_from_stream, save_jumbf_to_stream},
    Builder, BuilderIntent, Context, DigitalSourceType, Reader, SigningAlg,
};
use serde_json::json;

const GENERATOR: &str = "c2pa-rs test file generator";

fn certs_dir() -> Result<PathBuf> {
    let dir = std::env::var("C2PA_CERTS").context("C2PA_CERTS is not set")?;
    Ok(PathBuf::from(dir))
}

fn format_of(path: &Path) -> Result<String> {
    path.extension()
        .and_then(|e| e.to_str())
        .map(str::to_lowercase)
        .with_context(|| format!("{} has no extension", path.display()))
}

fn title_of(path: &Path) -> String {
    path.file_name()
        .and_then(|n| n.to_str())
        .unwrap_or_default()
        .to_string()
}

fn context(trust: bool) -> Result<Context> {
    let mut settings = json!({
        "builder": {"thumbnail": {"enabled": false}},
        "verify": {"ocsp_fetch": false, "remote_manifest_fetch": false}
    });
    if trust {
        let anchors = std::fs::read_to_string(certs_dir()?.join("trust/test_cert_root_bundle.pem"))?;
        settings["trust"] = json!({"trust_anchors": anchors});
    }
    Ok(Context::new().with_settings(settings.to_string().as_str())?)
}

fn builder(dest: &Path, actions: serde_json::Value) -> Result<Builder> {
    let definition = json!({
        "title": title_of(dest),
        "claim_generator_info": [{"name": GENERATOR, "version": env!("CARGO_PKG_VERSION")}],
        "assertions": [{"label": "c2pa.actions.v2", "data": {"actions": actions}}],
    });
    Ok(Builder::from_context(context(true)?).with_definition(definition.to_string())?)
}

fn sign(mut builder: Builder, source: &Path, dest: &Path) -> Result<()> {
    let certs = certs_dir()?;
    let cert = std::fs::read(certs.join("es256.pub"))?;
    let key = std::fs::read(certs.join("es256.pem"))?;
    let signer = create_signer::from_keys(&cert, &key, SigningAlg::Es256, None)?;
    if dest.exists() {
        std::fs::remove_file(dest)?;
    }
    builder
        .sign_file(signer.as_ref(), source, dest)
        .with_context(|| format!("signing {} -> {}", source.display(), dest.display()))?;
    Ok(())
}

fn add_ingredient(builder: &mut Builder, path: &Path, relationship: &str) -> Result<String> {
    let id = title_of(path);
    let ingredient = json!({"title": id, "relationship": relationship, "label": id});
    let mut stream = File::open(path)?;
    builder.add_ingredient_from_stream(ingredient.to_string(), &format_of(path)?, &mut stream)?;
    Ok(id)
}

fn create(source: &Path, dest: &Path, description: &str) -> Result<()> {
    let actions = json!([{
        "action": "c2pa.created",
        "digitalSourceType": DigitalSourceType::AlgorithmicMedia,
        "description": description,
    }]);
    let mut builder = builder(dest, actions)?;
    builder.set_intent(BuilderIntent::Create(DigitalSourceType::AlgorithmicMedia));
    sign(builder, source, dest)
}

fn edit(source: &Path, parent: &Path, dest: &Path, description: &str, components: &[PathBuf]) -> Result<()> {
    let mut builder = builder(dest, json!([]))?;
    let parent_id = add_ingredient(&mut builder, parent, "parentOf")?;
    builder.add_action(json!({
        "action": "c2pa.opened",
        "parameters": {"ingredientIds": [parent_id]},
    }))?;
    builder.add_action(json!({"action": "c2pa.edited", "description": description}))?;
    for component in components {
        let id = add_ingredient(&mut builder, component, "componentOf")?;
        builder.add_action(json!({
            "action": "c2pa.placed",
            "parameters": {"ingredientIds": [id]},
        }))?;
    }
    builder.set_intent(BuilderIntent::Edit);
    sign(builder, source, dest)
}

fn rfind(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack.windows(needle.len()).rposition(|w| w == needle)
}

fn be32(data: &[u8], at: usize) -> usize {
    u32::from_be_bytes(data[at..at + 4].try_into().unwrap()) as usize
}

/// Flip the last byte of the active manifest's COSE_Sign1, which is the signature.
fn tamper_signature(store: &mut [u8]) -> Result<()> {
    let label = rfind(store, b"c2pa.signature\0").context("no c2pa.signature box")?;
    let jumd = label - 25; // LBox, TBox, 16-byte UUID, toggles
    ensure!(&store[jumd + 4..jumd + 8] == b"jumd", "unexpected signature box layout");
    let cbor = jumd + be32(store, jumd);
    ensure!(&store[cbor + 4..cbor + 8] == b"cbor", "signature box has no cbor content");
    let end = cbor + be32(store, cbor);
    store[end - 1] ^= 0xFF;
    Ok(())
}

/// Change the case of the first letter of the last occurrence of `text`:
/// still valid CBOR, but the assertion no longer matches its hashed URI.
fn tamper_text(store: &mut [u8], text: &str) -> Result<()> {
    let at = rfind(store, text.as_bytes()).with_context(|| format!("no {text:?} in the manifest store"))?;
    store[at] ^= 0x20;
    Ok(())
}

fn embed(from: &Path, into: &Path, dest: &Path, tamper: &[String]) -> Result<()> {
    let mut store = load_jumbf_from_stream(&format_of(from)?, &mut File::open(from)?)?;
    match tamper {
        [] => {}
        [kind] if kind == "sig" => tamper_signature(&mut store)?,
        [kind, text] if kind == "uri" => tamper_text(&mut store, text)?,
        _ => bail!("unknown tamper {tamper:?}"),
    }
    let input = std::fs::read(into)?;
    let mut output = std::io::Cursor::new(Vec::new());
    save_jumbf_to_stream(&format_of(into)?, &mut std::io::Cursor::new(input), &mut output, &store)?;
    std::fs::write(dest, output.into_inner())?;
    Ok(())
}

fn read(asset: &Path, out_dir: &Path) -> Result<()> {
    let reader = Reader::from_context(context(true)?).with_file(asset)?;
    std::fs::create_dir_all(out_dir)?;
    std::fs::write(out_dir.join("manifest_store.json"), reader.json() + "\n")?;
    std::fs::write(out_dir.join("detailed.json"), reader.detailed_json() + "\n")?;
    println!("{}: {:?}", title_of(asset), reader.validation_state());
    Ok(())
}

fn main() -> Result<()> {
    let args: Vec<PathBuf> = std::env::args_os().skip(1).map(PathBuf::from).collect();
    let text = |p: &PathBuf| p.to_string_lossy().into_owned();
    match args.first().and_then(|a| a.to_str()) {
        Some("create") if args.len() == 4 => create(&args[1], &args[2], &text(&args[3])),
        Some("edit") if args.len() >= 5 => edit(&args[1], &args[2], &args[3], &text(&args[4]), &args[5..]),
        Some("embed") if args.len() >= 4 => {
            let tamper: Vec<String> = args[4..].iter().map(text).collect();
            embed(&args[1], &args[2], &args[3], &tamper)
        }
        Some("read") if args.len() == 3 => read(&args[1], &args[2]),
        _ => bail!(
            "usage: make_testfile create <source> <dest> <description>\n       \
             make_testfile edit <source> <parent> <dest> <description> [<component>...]\n       \
             make_testfile embed <store-from> <into> <dest> [sig | uri <text>]\n       \
             make_testfile read <asset> <out-dir>"
        ),
    }
}
