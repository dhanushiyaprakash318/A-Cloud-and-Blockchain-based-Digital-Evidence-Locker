require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  defaultNetwork: "hardhat",
  networks: {
    hardhat: {},
    localhost: {
      url: process.env.RPC_URL || "http://127.0.0.1:8545",
      chainId: 31337,
    },
    sepolia: {
      url: process.env.RPC_URL || "",
      accounts: (process.env.PRIVATE_KEY || process.env.BLOCKCHAIN_PRIVATE_KEY)
        ? [(process.env.PRIVATE_KEY || process.env.BLOCKCHAIN_PRIVATE_KEY)]
        : [],
      chainId: 11155111,
      timeout: 60000,
    },
  },
};