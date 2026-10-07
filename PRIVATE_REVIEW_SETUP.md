# Private genre review setup

The review page is an additional Streamlit page; ordinary playlist sequencing remains available. This page never loads private data until Google login and the owner allowlist both succeed. No private library, account credentials, or existing decisions are bundled in GitHub. It initially permits one verified Google-account email. Phone and desktop use the same owner identity and cloud revision.

## Account setup before going live

1. In your Google Cloud account, create an OAuth web client, enable Google identity, and register `https://mixweave-dj.streamlit.app/oauth2callback` as the authorized redirect. Add your Google account as a test user if using an external app in testing mode. Obtain client ID and secret.
2. Create a Supabase project in your account. Run `setup/private_review.sql` in its SQL editor. The script creates a private bucket, service-only table and revision-checked save function. It does not grant anonymous or authenticated public clients access. If a bucket with that name already exists and is public, make it private; the app refuses a public bucket. Verify storage object policies do not grant anonymous access to this bucket.
3. In Streamlit Cloud's app settings, add the values shown in `setup/secrets.example.toml`. Real secrets stay in the Streamlit secret manager. Set exactly one owner email. The Supabase service key is used only by Python on the server and must never appear in browser code or GitHub.
4. Merge the reviewed implementation and wait for Streamlit dependencies to install. Open Genre Review, sign in, upload the master CSV once, and optionally import your saved desktop decision JSON. No file is automatically uploaded by this change.
5. From the phone, open MixWeave's Genre Review page and sign in using the same account. Saved group and song choices are loaded from the private store. Choose Save group choice or Save song choice to persist; closing a form without saving does not save it.

## Concurrent edits

Saves compare the loaded revision with the server's current revision in one database operation. An older device cannot silently overwrite newer choices. On a conflict, download the local decisions backup, then reload the cloud copy before continuing. Manual imports replace the saved decisions after a revision check; they do not merge conflicting choices automatically.

## Privacy and verification

The bucket must remain private. The owner identity derives from Google's stable issuer/subject, not a client-supplied email or file path. Authorization precedes all storage access. Uploaded CSVs have unique-file and size validation; objects use immutable names and integrity hashes. Failed uploads/saves are not reported as successful. The server key bypasses storage RLS, so restrict access to deployment secrets and do not reuse the backend for arbitrary browser requests.

A successful cloud upload followed by a manifest-save conflict can leave an unreferenced private object. It does not replace the active library; remove orphan objects manually later if needed. Supabase remains the external store of private library/decision data until the owner deletes it. Streamlit local disk is not used as the durable store.

Before calling the feature live, verify: owner login, denied second account, logout, private bucket access, uploading/restoring desktop decisions, saving on desktop then loading on phone, stale-session conflict, and backup export. Local mocked tests do not establish actual OAuth or hosted storage access.

Official configuration references: [Streamlit authentication](https://docs.streamlit.io/develop/concepts/connections/authentication), [Supabase access controls](https://supabase.com/docs/guides/storage/security/access-control), and [private buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals).
