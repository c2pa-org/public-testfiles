# Google-contributed validator test cases

These are validator test cases produced using Google-internal tooling.

Please report test issues via
https://github.com/c2pa-org/public-testfiles/issues/new

## Contents:

  *  `assets/` - media files, in various formats
  *  `certs/` - PEM-format x.509 certificates
  *  `tests/` - validator test cases referencing the files in `assets` and
     `certificates`
  
## Test case schema

Test cases are specified as YAML files, following the JSON schema in
`validator_test_case.schema.json`, which is summarized here:

  * `description` - description of the test case
  * `inputs` - validator inputs
	* `asset_path` - path to the asset to validate
	* `claim_signer_trust_list_paths` - paths to PEM files comprising the (test)
	  C2PA Trust List to use. Each file contains one or more trust anchors.
	  The validator should use these instead of the standard C2PA Trust List, as
	  the trust list associated with the c2pa-kp-claimSigning EKU.
    * `tsa_trust_list_paths` - paths to PEM files comprising the (test) C2PA
	  TSA Trust List to use. Each file contains one or more trust anchors.
	  The validator should use these instead of the standard C2PA TSA Trust List.
    * `validation_time` - the time the validator should treat as "now", instead
	  of using a system clock. RFC 3339 format, e.g., "2010-03-21T15:30:00Z".
  * `manifests` - expected validation results for each manifest in the manifest
    store, listed in the reverse order of appearance in the manifest store
    (active manifest first, as in crJSON).
    * `failures` - expectations regarding validator failure codes
    * `successes` - expectations regarding validator success codes
    * `informationals` - expectations regarding validator informational codes
  * `validatorSpecVersions` - optional list of C2PA spec version(s) that this
    test case applies to (e.g., "2.4"). If empty, the test case is assumed to
    apply to all spec versions.

Status code expectations are expressed using a `StatusCodesExpectations` object,
containing zero or more of the following fields, each of which represents a
separate expectation that must be satisfied with respect to a set of status
codes produced by the validator:
  * `is_empty` (value is an empty object) - set must be empty
  * `is_not_empty` (value is an empty object) - set must be non-empty
  * `contains_exactly` (value is a StatusCodeSet object) - set must contain exactly the listed codes
  * `contains_all_of` (value is a StatusCodeSet object) - set must contain all of the listed codes
  * `contains_none_of` (value is a StatusCodeSet object) - set must contain none of the listed codes
  * `contains_any_of` (value is an array of StatusCodeSet objects) - set must contain at least one code from each of the listed sets
  
A `StatusCodeSet` object contains just one field:
  * `codes` - an array of status code strings (e.g. "signingCredential.trusted")

This is not an officially supported Google product. This project is not eligible
for the [Google Open Source Software Vulnerability Rewards Program](https://bughunters.google.com/open-source-security).
