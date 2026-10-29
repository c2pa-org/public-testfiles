//! Sign and read the audio test files in `2.4/audio`.
//!
//! Usage:
//!   make_audio create <source> <dest> <description>
//!   make_audio edit <source> <parent> <dest> <description> [<component>...]
//!   make_audio read <asset> <out-dir>
//!
//! `create` signs a newly synthesised asset (`c2pa.created`, algorithmicMedia).
//! `edit` signs an edited asset with `parent` as its parentOf ingredient and
//! each `component` as a componentOf ingredient (`c2pa.opened`, `c2pa.edited`,
//! and one `c2pa.placed` per component).
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

use anyhow::{bail, Context as _, Result};
use c2pa::{
    create_signer, Builder, BuilderIntent, Context, DigitalSourceType, Reader, SigningAlg,
};
use serde_json::json;

const GENERATOR: &str = "c2pa-rs audio test file generator";

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
        Some("read") if args.len() == 3 => read(&args[1], &args[2]),
        _ => bail!(
            "usage: make_audio create <source> <dest> <description>\n       \
             make_audio edit <source> <parent> <dest> <description> [<component>...]\n       \
             make_audio read <asset> <out-dir>"
        ),
    }
}
