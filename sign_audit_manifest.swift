// sign_audit_manifest.swift
//
// Run this once, by hand, whenever a batch of content has actually been
// reviewed by the theological reviewer and you're ready to mark it
// "audited" for real. This is the ONLY way audit_status: "audited" has any
// effect in the app — see Saintly/Services/AuditManifestVerifier.swift for
// why a bare JSON field alone is never trusted.
//
// USAGE
//   1. In each topics/<slug>.json file, set "audit_status": "audited" on
//      whatever questions actually passed review (same as before).
//   2. Set the AUDIT_SIGNING_KEY environment variable to the private key
//      (see KEY CUSTODY below) -- never pass it as a command-line argument,
//      that ends up in shell history.
//   3. Run:
//        AUDIT_SIGNING_KEY="<the private key>" swift sign_audit_manifest.swift
//   4. It rewrites manifest.json's auditedQuestionIDs and auditSignature
//      fields in place. Commit and push manifest.json along with whatever
//      topic files you just marked audited. Note: it reformats the whole
//      file (pretty-printed, alphabetized keys) as a side effect of how it
//      rewrites JSON -- the content is unchanged, just the layout.
//
// KEY CUSTODY
//   The private key was generated once (Aug 12, 2026) and handed to you
//   directly -- see "andrew to do/AUDIT SIGNING KEY - keep this safe.txt"
//   in the Saintly repo. It does NOT live in this repo, the Saintly repo,
//   or anywhere else in source control, on purpose: anyone who has it can
//   forge an "audited" claim exactly as if this whole signature scheme
//   didn't exist. Store it in a password manager, not a plain text file
//   left lying around after your first read of it.
//
// WHAT THIS ACTUALLY PROVES
//   A valid signature proves "whoever ran this script had the private key,"
//   nothing more -- it's a technical control against the content REPO being
//   the sole source of truth (a compromised GitHub account or a stray PR
//   merge could otherwise set audit_status freely with zero pushback). It
//   is not a proof that a human theologian actually read every question;
//   that part is still on you to do honestly before running this.

import CryptoKit
import Foundation

struct TopicEntry: Decodable {
    let slug: String
    let file: String
}

struct ManifestShape: Decodable {
    let databaseVersion: String
    let topics: [TopicEntry]
}

struct QuestionAuditFields: Decodable {
    let id: String
    let audit_status: String?
}

struct TopicContentFile: Decodable {
    let questions: [QuestionAuditFields]
}

let repoRoot = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let manifestURL = repoRoot.appendingPathComponent("manifest.json")

guard let privateKeyBase64 = ProcessInfo.processInfo.environment["AUDIT_SIGNING_KEY"] else {
    FileHandle.standardError.write("Set AUDIT_SIGNING_KEY in the environment first. See this script's header.\n".data(using: .utf8)!)
    exit(1)
}
guard let privateKeyData = Data(base64Encoded: privateKeyBase64),
      let privateKey = try? Curve25519.Signing.PrivateKey(rawRepresentation: privateKeyData)
else {
    FileHandle.standardError.write("AUDIT_SIGNING_KEY isn't a valid base64-encoded Ed25519 private key.\n".data(using: .utf8)!)
    exit(1)
}

let manifestData = try! Data(contentsOf: manifestURL)
let manifest = try! JSONDecoder().decode(ManifestShape.self, from: manifestData)

var auditedIDs: [String] = []
for topic in manifest.topics {
    let fileURL = repoRoot.appendingPathComponent(topic.file)
    let data = try! Data(contentsOf: fileURL)
    let content = try! JSONDecoder().decode(TopicContentFile.self, from: data)
    auditedIDs.append(contentsOf: content.questions.filter { $0.audit_status == "audited" }.map(\.id))
}

let sortedIDs = auditedIDs.sorted()
let canonical = ([manifest.databaseVersion] + sortedIDs).joined(separator: "\n")
let signature = try! privateKey.signature(for: Data(canonical.utf8))
let signatureBase64 = signature.base64EncodedString()

// Rewrite manifest.json in place, touching only the two signature fields —
// everything else (topic list, totals, description) passes through exactly
// as it was, whatever order its keys happen to be in.
var json = try! JSONSerialization.jsonObject(with: manifestData) as! [String: Any]
json["auditedQuestionIDs"] = sortedIDs
json["auditSignature"] = signatureBase64

let output = try! JSONSerialization.data(withJSONObject: json, options: [.prettyPrinted, .sortedKeys])
try! output.write(to: manifestURL)

print("Signed \(sortedIDs.count) audited question IDs into manifest.json.")
print("Database version: \(manifest.databaseVersion)")
