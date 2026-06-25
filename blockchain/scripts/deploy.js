const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    console.log("Deploying EvidenceRegistry...");

    const EvidenceRegistry = await hre.ethers.getContractFactory("EvidenceRegistry");
    const evidenceRegistry = await EvidenceRegistry.deploy();

    await evidenceRegistry.waitForDeployment();

    const address = await evidenceRegistry.getAddress();

    console.log(`EvidenceRegistry deployed to: ${address}`);

    // Save the address and ABI to a file backend can read easily
    const deployData = {
        address: address,
        network: hre.network.name,
        abi: JSON.parse(fs.readFileSync(path.resolve(__dirname, "../artifacts/contracts/EvidenceRegistry.sol/EvidenceRegistry.json"), "utf8")).abi
    };

    // Save to backend folder for easy access
    const backendConfigPath = path.resolve(__dirname, "../../backend/app/blockchain_config.json");
    fs.writeFileSync(backendConfigPath, JSON.stringify(deployData, null, 2));
    console.log(`Config saved to ${backendConfigPath}`);
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
