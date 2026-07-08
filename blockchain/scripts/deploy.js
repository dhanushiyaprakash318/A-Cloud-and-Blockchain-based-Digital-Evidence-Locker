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
    const networkName = hre.network.name;
    console.log(`Deploying EvidenceRegistry to ${networkName}...`);

    await ensureNetworkConfig(networkName);

    const [deployer] = await hre.ethers.getSigners();
    console.log(`Deployer account: ${deployer.address}`);

    const EvidenceRegistry = await hre.ethers.getContractFactory("EvidenceRegistry");
    const evidenceRegistry = await EvidenceRegistry.deploy();
    await evidenceRegistry.waitForDeployment();

    const deploymentReceipt = await evidenceRegistry.deploymentTransaction()?.wait();
    const address = await evidenceRegistry.getAddress();
    const network = await hre.ethers.provider.getNetwork();

    const artifactPath = path.resolve(__dirname, "../artifacts/contracts/EvidenceRegistry.sol/EvidenceRegistry.json");
    if (!fs.existsSync(artifactPath)) {
        throw new Error(`Hardhat artifact not found at ${artifactPath}`);
    }

    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    const contractArtifact = {
        contractName: artifact.contractName,
        abi: artifact.abi,
        bytecode: artifact.bytecode,
        deployedBytecode: artifact.deployedBytecode,
    };

    const buildArtifactPath = path.resolve(__dirname, "../artifacts/EvidenceRegistry.json");
    writeJson(buildArtifactPath, contractArtifact);

    const deploymentSummary = {
        network: networkName,
        chainId: Number(network.chainId),
        contractAddress: address,
        rpcUrl: hre.network.config.url || "http://127.0.0.1:8545",
        deployedAt: new Date().toISOString(),
    };

    const deployAddressPath = path.resolve(__dirname, "../deployed-address.json");
    writeJson(deployAddressPath, deploymentSummary);

    const repoRoot = path.resolve(__dirname, "../..");
    const backendConfigPath = path.resolve(repoRoot, "backend/app/blockchain_config.json");
    const addressFilePath = path.resolve(repoRoot, "contract-address.json");

    writeJson(backendConfigPath, {
        ...deploymentSummary,
        address,
        abi: artifact.abi,
    });
    writeJson(addressFilePath, {
        contract_address: address,
        network: networkName,
        rpc_url: deploymentSummary.rpcUrl,
    });

    console.log(`Contract Address : ${address}`);
    console.log(`Transaction Hash : ${deploymentReceipt?.hash || "n/a"}`);
    console.log(`Network          : ${networkName}`);
    console.log(`Gas Used         : ${deploymentReceipt?.gasUsed?.toString() || "n/a"}`);
    console.log(`ABI saved to ${buildArtifactPath}`);
    console.log(`Address saved to ${deployAddressPath}`);
    console.log(`Backend config saved to ${backendConfigPath}`);
}

main()
    .then(() => {
        process.exit(0);
    })
    .catch((error) => {
        console.error("Deployment failed:", error.message || error);
        process.exit(1);
    });
