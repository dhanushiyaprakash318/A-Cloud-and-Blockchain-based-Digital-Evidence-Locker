/**
 * prove_hash.js
 * 
 * STEP 1: Stores a demo evidence hash ON-CHAIN
 * STEP 2: Reads it back from the contract to PROVE it was stored
 * 
 * Run: npx hardhat run scripts/prove_hash.js --network localhost
 */

const hre = require("hardhat");
const crypto = require("crypto");

async function main() {
  console.log("\n============================================================");
  console.log("  DIVEL - BLOCKCHAIN HASH PROOF DEMONSTRATION");
  console.log("============================================================\n");

  // --- SETUP ---
  const contractAddress = "0x5FbDB2315678afecb367f032d93F642f64180aa3";
  const EvidenceRegistry = await hre.ethers.getContractFactory("EvidenceRegistry");
  const contract = await EvidenceRegistry.attach(contractAddress);

  const [deployer] = await hre.ethers.getSigners();
  console.log(`📡 Connected to Hardhat Node`);
  console.log(`🔑 Using account: ${deployer.address}\n`);

  // --- STEP 1: Simulate a file and compute its SHA-256 hash ---
  const demoFileContent = "DEMO_EVIDENCE_FILE: fingerprint_scan_suspect_A.png | Case: FIR-2025-001 | Uploaded by: Forensics Officer";
  const fileHash = crypto.createHash("sha256").update(demoFileContent).digest("hex");

  const evidenceId   = "DEMO-EVD-" + Date.now();
  const caseId       = "DEMO-CASE-FIR-2025-001";
  const fileType     = "image/png";
  const uploaderRole = "Forensics Officer";
  const previousHash = "";

  console.log("📄 SIMULATED FILE CONTENT:");
  console.log(`   "${demoFileContent}"`);
  console.log("\n🔒 COMPUTED SHA-256 HASH:");
  console.log(`   ${fileHash}`);
  console.log("\n📋 METADATA:");
  console.log(`   Evidence ID  : ${evidenceId}`);
  console.log(`   Case ID      : ${caseId}`);
  console.log(`   File Type    : ${fileType}`);
  console.log(`   Uploader Role: ${uploaderRole}`);

  // --- STEP 2: Store the hash ON-CHAIN ---
  console.log("\n⛓️  WRITING HASH TO BLOCKCHAIN...");
  const tx = await contract.anchorEvidence(
    evidenceId,
    fileHash,
    fileType,
    caseId,
    uploaderRole,
    previousHash
  );
  const receipt = await tx.wait();

  console.log(`✅ TRANSACTION CONFIRMED!`);
  console.log(`   Transaction Hash : ${receipt.hash}`);
  console.log(`   Block Number     : ${receipt.blockNumber}`);
  console.log(`   Gas Used         : ${receipt.gasUsed.toString()}`);

  // --- STEP 3: Read hash BACK from chain to prove it's stored ---
  console.log("\n🔍 READING HASH BACK FROM BLOCKCHAIN CONTRACT...");
  const storedEvidence = await contract.getEvidence(evidenceId);

  console.log("\n============================================================");
  console.log("  ✅ PROOF: HASH RETRIEVED FROM BLOCKCHAIN");
  console.log("============================================================");
  console.log(`   Evidence ID      : ${storedEvidence.evidenceId}`);
  console.log(`   Case ID          : ${storedEvidence.caseId}`);
  console.log(`   File Type        : ${storedEvidence.fileType}`);
  console.log(`   Uploader Role    : ${storedEvidence.uploaderRole}`);
  console.log(`   Uploader Address : ${storedEvidence.uploaderAddress}`);
  console.log(`   Timestamp (Unix) : ${storedEvidence.timestamp.toString()}`);
  console.log(`   Timestamp (Date) : ${new Date(Number(storedEvidence.timestamp) * 1000).toLocaleString()}`);
  console.log(`\n   📌 STORED FILE HASH (on-chain):`);
  console.log(`   ${storedEvidence.fileHash}`);

  // --- STEP 4: Verify the hash matches ---
  console.log("\n============================================================");
  console.log("  🔐 INTEGRITY VERIFICATION");
  console.log("============================================================");
  const matches = storedEvidence.fileHash === fileHash;
  console.log(`   Computed Hash   : ${fileHash}`);
  console.log(`   On-Chain Hash   : ${storedEvidence.fileHash}`);
  console.log(`\n   ✅ MATCH: ${matches ? "YES — Hash is INTACT. Evidence NOT tampered." : "NO — MISMATCH DETECTED!"}`);

  // --- STEP 5: Simulate tampering ---
  console.log("\n============================================================");
  console.log("  ⚠️  TAMPER SIMULATION");
  console.log("============================================================");
  const tamperedContent = demoFileContent + " [TAMPERED]";
  const tamperedHash = crypto.createHash("sha256").update(tamperedContent).digest("hex");
  const tamperedMatch = storedEvidence.fileHash === tamperedHash;

  console.log(`   Tampered Hash   : ${tamperedHash}`);
  console.log(`   On-Chain Hash   : ${storedEvidence.fileHash}`);
  console.log(`\n   🚨 MATCH: ${tamperedMatch ? "YES" : "NO — TAMPER DETECTED! Hashes do NOT match."}`);

  console.log("\n============================================================");
  console.log("  DEMO COMPLETE — Hash is permanently stored on-chain.");
  console.log("  Contract: " + contractAddress);
  console.log("============================================================\n");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
