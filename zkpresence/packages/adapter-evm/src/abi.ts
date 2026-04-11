/**
 * ZkPresence.sol ABI — minimal ABI for the contract interface.
 *
 * In Phase 1, this will be generated from `forge inspect ZkPresence abi`.
 * For now, hand-written to match the contract.
 */

export const zkPresenceAbi = [
  {
    type: 'constructor',
    inputs: [
      { name: '_verifier', type: 'address' },
      { name: '_programVKey', type: 'bytes32' },
    ],
  },
  {
    type: 'function',
    name: 'createEvent',
    inputs: [
      { name: 'locationHash', type: 'bytes32' },
      { name: 'startTime', type: 'uint64' },
      { name: 'endTime', type: 'uint64' },
      { name: 'organizerPubkeyHash', type: 'bytes32' },
    ],
    outputs: [{ name: 'eventId', type: 'uint64' }],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    name: 'verifyAttendance',
    inputs: [
      { name: 'proof', type: 'bytes' },
      { name: 'publicValues', type: 'bytes' },
    ],
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    name: 'hasAttended',
    inputs: [
      { name: 'eventId', type: 'uint64' },
      { name: 'identityCommitment', type: 'bytes32' },
    ],
    outputs: [{ type: 'bool' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    name: 'isNullifierUsed',
    inputs: [{ name: 'nullifier', type: 'bytes32' }],
    outputs: [{ type: 'bool' }],
    stateMutability: 'view',
  },
  {
    type: 'function',
    name: 'getEvent',
    inputs: [{ name: 'eventId', type: 'uint64' }],
    outputs: [
      {
        type: 'tuple',
        components: [
          { name: 'organizer', type: 'address' },
          { name: 'locationHash', type: 'bytes32' },
          { name: 'startTime', type: 'uint64' },
          { name: 'endTime', type: 'uint64' },
          { name: 'organizerPubkeyHash', type: 'bytes32' },
          { name: 'active', type: 'bool' },
        ],
      },
    ],
    stateMutability: 'view',
  },
  {
    type: 'function',
    name: 'deactivateEvent',
    inputs: [{ name: 'eventId', type: 'uint64' }],
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    type: 'function',
    name: 'eventCount',
    inputs: [],
    outputs: [{ type: 'uint64' }],
    stateMutability: 'view',
  },
  {
    type: 'event',
    name: 'EventCreated',
    inputs: [
      { name: 'eventId', type: 'uint64', indexed: true },
      { name: 'organizer', type: 'address', indexed: true },
    ],
  },
  {
    type: 'event',
    name: 'EventDeactivated',
    inputs: [
      { name: 'eventId', type: 'uint64', indexed: true },
    ],
  },
  {
    type: 'event',
    name: 'AttendanceVerified',
    inputs: [
      { name: 'eventId', type: 'uint64', indexed: true },
      { name: 'nullifier', type: 'bytes32', indexed: true },
      { name: 'identityCommitment', type: 'bytes32', indexed: false },
      { name: 'attestationMode', type: 'uint8', indexed: false },
    ],
  },
] as const;
