# Deploying to Sepolia

1. Install dependencies:

```bash
npm install
```

2. Compile the contract:

```bash
npx hardhat compile
```

3. Deploy to Sepolia:

```bash
npx hardhat run scripts/deploy.js --network sepolia
```

4. Ensure the backend can read the generated configuration file:

- The deployment script writes backend/app/blockchain_config.json automatically.
- The backend service reads that file on startup and uses the deployed contract ABI and address without code changes.

5. Add your environment variables in the blockchain/.env file:

```env
PRIVATE_KEY=your_private_key_here
SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/your-api-key
```

> Do not commit your .env file. Keep it local only.
