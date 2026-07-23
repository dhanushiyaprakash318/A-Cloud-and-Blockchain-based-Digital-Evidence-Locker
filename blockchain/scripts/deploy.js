const hre = require("hardhat");
const fs = require("fs");
const path = require("path");
function writeJson(filePath, data) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`);
}

async function ensureNetworkConfig(networkName) {
    if (networkName === "sepolia") {
        if (!process.env.RPC_URL) {
            throw new Error("Missing RPC_URL in .env for Sepolia deployment.");
        }
        const privateKey = process.env.PRIVATE_KEY || process.env.BLOCKCHAIN_PRIVATE_KEY;
        if (!privateKey) {
            throw new Error("Missing PRIVATE_KEY in .env for Sepolia deployment.");
        }
    }
}

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
