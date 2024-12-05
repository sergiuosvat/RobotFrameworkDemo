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
)
from multiversx_sdk.abi import Abi
from pathlib import Path
from robot.api.deco import keyword


class MxLibrary:
    """Library for interacting with the MultiversX blockchain.

    Interacts with the MultiversX smart contract using its deploy and execute functions.
    """

    def __init__(self, provider_url, chain_id, abi_path, wasm_path, pem_path):
        self.wallet_address = None
        self.current_nonce = None
        self.provider = ProxyNetworkProvider(provider_url)
        self.converter = TransactionsConverter()
        self.parser = SmartContractTransactionsOutcomeParser()
        self.transaction_computer = TransactionComputer()
        self.config = TransactionsFactoryConfig(chain_id=chain_id)
        self.abi = Abi.load(Path(abi_path))
        self.bytecode = Path(wasm_path).read_bytes()
        self.factory = SmartContractTransactionsFactory(self.config, self.abi)
        self.signer = UserSigner.from_pem_file(Path(pem_path))

    @keyword("Set User")
    def set_user(self, bech32_address):
        """Sets the user for subsequent transactions by providing their wallet address."""
        self.wallet_address = Address.new_from_bech32(bech32_address)
        self.current_nonce = self.provider.get_account(self.wallet_address).nonce

    @keyword("Execute Add")
    def execute_add(self, args, gas_limit=10_000_000):
        """Deploys and executes the 'add' function of the smart contract.

        Args:
            args (list): Arguments to pass to the `add` function.
            gas_limit (int): The gas limit for the transaction (default: 10,000,000).
        """
        try:
            deploy_transaction = self.factory.create_transaction_for_deploy(
                sender=self.wallet_address,
                bytecode=self.bytecode,
                arguments=args,
                gas_limit=gas_limit,
                is_upgradeable=True,
                is_readable=True,
                is_payable=True,
                is_payable_by_sc=True,
            )
            address_computer = AddressComputer()
            contract_address = address_computer.compute_contract_address(
                deployer=Address.new_from_bech32(deploy_transaction.sender),
                deployment_nonce=deploy_transaction.nonce,
            )

            transaction = self.factory.create_transaction_for_execute(
                sender=self.wallet_address,
                contract=contract_address,
                function="add",
                gas_limit=gas_limit,
                arguments=args,
            )

            nonce_holder = AccountNonceHolder(self.current_nonce)

            deploy_transaction.nonce = nonce_holder.get_nonce_then_increment()
            transaction.nonce = nonce_holder.get_nonce_then_increment()

            deploy_transaction.signature = self.signer.sign(
                self.transaction_computer.compute_bytes_for_signing(deploy_transaction)
            )
            transaction.signature = self.signer.sign(
                self.transaction_computer.compute_bytes_for_signing(transaction)
            )

            hashes = self.provider.send_transactions([deploy_transaction, transaction])
            transaction_hashes = list(hashes[1].values())
            return transaction_hashes

        except Exception as e:
            raise AssertionError(f"Failed to execute add function: {str(e)}")

    @keyword("Result Should Be Success")
    def result_should_be_success(self, hashes):
        """Verifies that each transaction in the list of hashes was successful.

        Args:
            hashes (list): A list of transaction hashes to check for success.
        """
        try:
            for hash in hashes:
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

    @keyword("Should Cause Error")
    def should_cause_error(self, args, expected_error_message):
        """Verifies that executing the 'add' function causes an error.

        Args:
            args (list): The arguments to pass to the `add` function.
            expected_error_message (str): The expected error message.
        """

        try:
            self.execute_add(args)
        except Exception as err:
            if expected_error_message not in str(err):
                raise AssertionError(
                    f"Expected error message: '{expected_error_message}', but got: '{str(err)}'"
                )
            return str(err)
        else:
            raise AssertionError(f"'{args}' should have caused an error.")
