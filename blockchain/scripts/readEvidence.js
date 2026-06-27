const { ethers } = require("hardhat");

async function main() {
    const contractAddress = "0x5FbDB2315678afecb367f032d93F642f64180aa3";
    const contract = await ethers.getContractAt(
        "EvidenceRegistry",
        contractAddress
    );

    const evidenceId = "PASTE_EVIDENCE_ID_HERE";
    const data = await contract.getEvidence(evidenceId);

    console.log("Evidence ID :", data[0]);
    console.log("Stored Hash :", data[1]);
    console.log("File Type   :", data[2]);
    console.log("Case ID     :", data[3]);
    console.log("Role        :", data[4]);
    console.log("Timestamp   :", data[5].toString());
}

main().catch(console.error);
