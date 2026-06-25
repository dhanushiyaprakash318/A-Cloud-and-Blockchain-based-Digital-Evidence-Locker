// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract EvidenceRegistry {
    struct Evidence {
        string evidenceId;
        string fileHash;
        string fileType;
        string caseId;
        string uploaderRole;
        uint256 timestamp;
        string previousHash; // For chain of custody
        address uploaderAddress;
    }

    mapping(string => Evidence) public evidences;
    string[] public evidenceIds;

    event EvidenceAnchored(
        string indexed evidenceId,
        string indexed caseId,
        string fileHash,
        address indexed uploader
    );

    function anchorEvidence(
        string memory _evidenceId,
        string memory _fileHash,
        string memory _fileType,
        string memory _caseId,
        string memory _uploaderRole,
        string memory _previousHash
    ) public {
        // Ensure evidence ID is unique
        require(bytes(evidences[_evidenceId].evidenceId).length == 0, "Evidence already exists");

        Evidence memory newEvidence = Evidence({
            evidenceId: _evidenceId,
            fileHash: _fileHash,
            fileType: _fileType,
            caseId: _caseId,
            uploaderRole: _uploaderRole,
            timestamp: block.timestamp,
            previousHash: _previousHash,
            uploaderAddress: msg.sender
        });

        evidences[_evidenceId] = newEvidence;
        evidenceIds.push(_evidenceId);

        emit EvidenceAnchored(_evidenceId, _caseId, _fileHash, msg.sender);
    }

    function getEvidence(string memory _evidenceId) public view returns (Evidence memory) {
        return evidences[_evidenceId];
    }
    
    function verifyHash(string memory _evidenceId, string memory _computedHash) public view returns (bool) {
        if (bytes(evidences[_evidenceId].evidenceId).length == 0) {
            return false;
        }
        return (keccak256(abi.encodePacked(evidences[_evidenceId].fileHash)) == keccak256(abi.encodePacked(_computedHash)));
    }
}
