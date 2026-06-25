// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title EvidenceLedger
 * @dev Immutable ledger for Digital Evidence.
 *      Stores cryptographic hashes and metadata for court verification.
 */
contract EvidenceLedger {
    
    enum Role { NONE, OFFICER, LAB_TECH, JUDGE, ADMIN }
    
    struct Evidence {
        string evidenceId;     // UUID from the application
        string caseId;
        string fileHash;       // SHA-256 Hash of the file content
        string fileType;       // MIME type (e.g., "video/mp4")
        uint256 timestamp;     // Block timestamp of anchoring
        address uploader;      // Wallet address of the uploader
        string uploaderRole;   // Role string (e.g. "Officer") for readability
        string previousHash;   // Pointer to previous evidence hash (Chain of Custody)
        bool exists;
    }
    
    mapping(string => Evidence) public evidenceStore;
    mapping(address => Role) public userRoles;
    
    // Indexing for easier lookup logs
    event EvidenceAnchored(
        string indexed caseId, 
        string indexed evidenceId, 
        address indexed uploader, 
        string fileHash,
        uint256 timestamp
    );
    
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not Owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        userRoles[msg.sender] = Role.ADMIN;
    }

    /**
     * @dev Simple RBAC for internal permissioned chain use
     */
    function grantRole(address _user, Role _role) external onlyOwner {
        userRoles[_user] = _role;
    }

    /**
     * @dev Anchors a new piece of evidence to the blockchain.
     *      Once written, this record CANNOT be modified.
     */
    function anchorEvidence(
        string memory _evidenceId,
        string memory _caseId,
        string memory _fileHash,
        string memory _fileType,
        string memory _uploaderRole,
        string memory _previousHash
    ) public {
        // checks
        require(!evidenceStore[_evidenceId].exists, "Evidence ID already exists");
        require(bytes(_evidenceId).length > 0, "ID required");
        require(bytes(_fileHash).length > 0, "Hash required");
        
        // In a strict private chain, we would require:
        // require(userRoles[msg.sender] != Role.NONE, "Unauthorized Uploader");

        // effects
        evidenceStore[_evidenceId] = Evidence({
            evidenceId: _evidenceId,
            caseId: _caseId,
            fileHash: _fileHash,
            fileType: _fileType,
            timestamp: block.timestamp,
            uploader: msg.sender,
            uploaderRole: _uploaderRole,
            previousHash: _previousHash,
            exists: true
        });
        
        // interactions
        emit EvidenceAnchored(_caseId, _evidenceId, msg.sender, _fileHash, block.timestamp);
    }
    
    /**
     * @dev verifier function for the Court/Judge
     */
    function verifyEvidence(string memory _evidenceId, string memory _computedHash) public view returns (bool) {
        if (!evidenceStore[_evidenceId].exists) {
            return false;
        }
        return (keccak256(bytes(evidenceStore[_evidenceId].fileHash)) == keccak256(bytes(_computedHash)));
    }
    
    /**
     * @dev Retrieve full details for UI display
     */
    function getEvidence(string memory _evidenceId) public view returns (Evidence memory) {
        require(evidenceStore[_evidenceId].exists, "Evidence not found");
        return evidenceStore[_evidenceId];
    }
}
