*** Settings ***
Library     MxLibrary.py    https://devnet-api.multiversx.com    D    ./contracts/adder.abi.json    ./contracts/adder.wasm    ./test_wallets/mike.pem


*** Test Cases ***
    
Execute Add Transaction
    [Documentation]    Deploy and execute the `add` function of the smart contract.
    Set User    erd1uv40ahysflse896x4ktnh6ecx43u7cmy9wnxnvcyp7deg299a4sq6vaywa
    ${args}=    Create List    42
    ${hashes}=    Execute Add    ${args}
    Log    Transaction hashes: ${hashes}
