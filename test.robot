*** Settings ***
Library     ./libraries/MxAddLibrary.py    https://devnet-api.multiversx.com    D    ./contracts/adder.abi.json    ./contracts/adder.wasm    ./test_wallets/mike.pem
Library     ./libraries/MxFactorialLibrary.py    https://devnet-api.multiversx.com    D    ./contracts/factorial.abi.json    ./contracts/factorial.wasm    ./test_wallets/mike.pem


*** Variables ***
${Sum}              0
${mike_address}     erd1uv40ahysflse896x4ktnh6ecx43u7cmy9wnxnvcyp7deg299a4sq6vaywa


*** Test Cases ***
Deploy Adder Contract, Execute Add Function, Deploy Factorial Contract, Execute Factorial Function
    [Documentation]    Deploy and execute the `add` function of the smart contract then check the sum
    MxAddLibrary.Set User    ${mike_address}
    ${args}=    Create List    2
    ${adder_contract_address}=    Deploy Adder    ${args}
    ${hash}    ${Sum}=    Execute Add    ${args}    ${adder_contract_address}
    Log    Transaction hash: ${hash}
    Log    Sum: ${Sum}
    MxAddLibrary.Result Should Be Success    ${hash}
    MxFactorialLibrary.Set User    ${mike_address}
    ${factorial_contract_address}=    Deploy Factorial
    ${hash_factorial}=    Execute Factorial    ${Sum}    ${factorial_contract_address}
    Log    Transaction hash: ${hash_factorial}
    MxFactorialLibrary.Result Should Be Success    ${hash_factorial}
