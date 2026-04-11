// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/ZkPresence.sol";

/// @title ZkPresence Deployment Script
/// @notice Deploy ZkPresence with the SP1 verifier gateway and program vkey.
/// @dev Usage: forge script script/Deploy.s.sol --rpc-url $RPC_URL --broadcast
contract DeployZkPresence is Script {
    function run() external {
        // SP1 Verifier Gateway (same address on all EVM chains via CREATE2)
        address verifier = vm.envAddress("SP1_VERIFIER_GATEWAY");
        bytes32 vkey = vm.envBytes32("ZKPRESENCE_VKEY");

        vm.startBroadcast();
        ZkPresence zkp = new ZkPresence(verifier, vkey);
        vm.stopBroadcast();

        console.log("ZkPresence deployed at:", address(zkp));
        console.log("Verifier:", verifier);
        console.log("Program vkey:");
        console.logBytes32(vkey);
    }
}
