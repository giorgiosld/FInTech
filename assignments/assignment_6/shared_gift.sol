// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SharedGift {
    address public owner;
    uint256 public targetAmount;
    uint256 public totalContributed;
    bool public isCompleted;
    mapping(address => uint256) public contributions;
    address[] public contributors;

    // Event emitted when a contribution is made
    event ContributionMade(address contributor, uint256 amount);
    // Event emitted when the gift is purchased
    event GiftPurchased(address purchaser, uint256 amount);

    // Constructor to initialize the contract with a target amount
    constructor(uint256 _targetAmount) {
        owner = msg.sender;
        targetAmount = _targetAmount;
        isCompleted = false;
    }

    // Function to contribute to the contract
    function contribute() public payable {
        require(!isCompleted, "Gift already purchased");
        require(msg.value > 0, "Must contribute something");

        if(contributions[msg.sender] == 0) {
            contributors.push(msg.sender);
        }

        contributions[msg.sender] += msg.value;
        totalContributed += msg.value;

        emit ContributionMade(msg.sender, msg.value);
    }

    // Function to purchase the gift once the target amount is reached
    function purchaseGift(address payable recipient) public {
        require(!isCompleted, "Gift already purchased");
        require(totalContributed >= targetAmount, "Target amount not reached");
        require(isContributor(msg.sender), "Only contributors can trigger purchase");

        isCompleted = true;
        recipient.transfer(totalContributed);

        emit GiftPurchased(recipient, totalContributed);
    }

    // Function to check if an address is a contributor
    function isContributor(address user) public view returns (bool) {
        return contributions[user] > 0;
    }

    // Function to get the list of all contributors
    function getContributors() public view returns (address[] memory) {
        return contributors;
    }
}