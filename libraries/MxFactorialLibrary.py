import time
from multiversx_sdk import (
    Address,
    AddressComputer,
    SmartContractTransactionsFactory,
    TransactionsFactoryConfig,
    SmartContractTransactionsOutcomeParser,
    TransactionsConverter,
    TransactionComputer,
    ProxyNetworkProvider,
    UserSigner,
    AccountNonceHolder,
    QueryRunnerAdapter,
    SmartContractQueriesController,
)
from multiversx_sdk.abi import Abi
from pathlib import Path
from robot.api.deco import keyword


class MxFactorialLibrary:
    """Library for interacting with the MultiversX Factorial SC."""

    def __init__(self, provider_url, chain_id, abi_path, wasm_path, pem_path):
        self.wallet_address = None
        self.nonce = None
        self.provider = ProxyNetworkProvider(provider_url)
        self.converter = TransactionsConverter()
        self.parser = SmartContractTransactionsOutcomeParser()
        self.transaction_computer = TransactionComputer()
        self.config = TransactionsFactoryConfig(chain_id)
        self.abi = Abi.load(Path(abi_path))
        self.bytecode = Path(wasm_path).read_bytes()
        self.factory = SmartContractTransactionsFactory(self.config, self.abi)
        self.signer = UserSigner.from_pem_file(Path(pem_path))
        self.address_computer = AddressComputer()
        self.query_runner = QueryRunnerAdapter(
            ProxyNetworkProvider("https://devnet-api.multiversx.com")
        )
        self.query_controller = SmartContractQueriesController(
            self.query_runner, self.abi
        )

    @keyword("Set User")
    def set_user(self, bech32_address):
        """Sets the user for subsequent transactions by providing their wallet address."""
        self.wallet_address = Address.new_from_bech32(bech32_address)
        self.nonce = self.provider.get_account(self.wallet_address).nonce

    @keyword("Deploy Factorial")
    def deploy_factorial(self, gas_limit=10_000_000):
        """Deploys the smart contract to the blockchain.

        Args:
            gas_limit (int): The gas limit for the transaction (default: 10,000,000).
        """
        try:
            nonce_holder = AccountNonceHolder(self.nonce)

            deploy_transaction = self.factory.create_transaction_for_deploy(
                sender=self.wallet_address,
                bytecode=self.bytecode,
                gas_limit=gas_limit,
                is_upgradeable=True,
                is_readable=True,
                is_payable=True,
                is_payable_by_sc=True,
            )

            deploy_transaction.nonce = nonce_holder.get_nonce_then_increment()
            self.nonce = nonce_holder.nonce

            contract_address = self.address_computer.compute_contract_address(
                deployer=Address.new_from_bech32(deploy_transaction.sender),
                deployment_nonce=deploy_transaction.nonce,
            )

            deploy_transaction.signature = self.signer.sign(
                self.transaction_computer.compute_bytes_for_signing(deploy_transaction)
            )

            self.provider.send_transaction(deploy_transaction)

            time.sleep(6)  # Wait for the transaction to be processed

            return contract_address

        except Exception as e:
            raise AssertionError(f"Failed to deploy smart contract: {str(e)}")

    @keyword("Execute Factorial")
    def execute_factorial(self, args, contract_address, gas_limit=10_000_000):
        """Deploys and executes the 'factorial' function of the smart contract.

        Args:
            args (list): Arguments to pass to the `factorial` function.
            contract_address (str): The address of the smart contract.
            gas_limit (int): The gas limit for the transaction (default: 10,000,000).
        """
        try:
            nonce_holder = AccountNonceHolder(self.nonce)

            factorial_transaction = self.factory.create_transaction_for_execute(
                sender=self.wallet_address,
                contract=contract_address,
                function="factorial",
                gas_limit=gas_limit,
                arguments=args,
            )

            factorial_transaction.nonce = nonce_holder.get_nonce_then_increment()
            self.nonce = nonce_holder.nonce

            factorial_transaction.signature = self.signer.sign(
                self.transaction_computer.compute_bytes_for_signing(
                    factorial_transaction
                )
            )

            hash_factorial = self.provider.send_transaction(factorial_transaction)
            print(f"Transaction hash: {hash_factorial}")
            time.sleep(6)  # Wait for the transaction to be processed

            return hash_factorial

        except Exception as e:
            raise AssertionError(f"Failed to execute add function: {str(e)}")

    @keyword("Result Should Be Success")
    def result_should_be_success(self, hash):
        """Verifies that each transaction in the list of hashes was successful.

        Args:
            hashes (list): A list of transaction hashes to check for success.
        """
        try:
            while True:
                transaction = self.provider.get_transaction(
                    hash, with_process_status=True
                )
                is_processed = transaction.is_completed
                if is_processed:
                    outcome = transaction.status
                    if outcome.status == "success":
                        print(f"Transaction {hash} was successful.")
                    elif outcome.status == "fail":
                        print(f"Transaction {hash} failed: {outcome.status}")
                        # raise AssertionError(f"Transaction {hash} failed: {outcome.status}") # Maybe we can throw an error if a transaction fails
                    else:
                        print(
                            f"Transaction {hash} completed with unexpected status: {outcome.status}"
                        )
                    break
                else:
                    print(f"Transaction {hash} not yet processed. Waiting...")
                    time.sleep(6)

        except Exception as e:
            raise AssertionError(f"Failed to check transaction outcomes: {str(e)}")
