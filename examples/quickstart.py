"""Quickstart: list chains, create an EVM->EVM order, and poll its status.

This only hits the public, no-auth GET endpoints. Creating the order returns an
unsigned transaction; signing/broadcasting is left to you (see the optional
``[exec]`` extra for web3.py / solders).

    python examples/quickstart.py
"""

from debridge import DebridgeClient
from debridge.constants import ChainId

# A real-looking address; the all-zero/dEaD address is compliance-blocked.
RECIPIENT = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
ARBITRUM_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"


def main() -> None:
    with DebridgeClient() as client:
        chains = client.get_supported_chains()
        print(f"deBridge supports {len(chains.chains)} chains:")
        for chain in chains.chains:
            print(f"  {chain.chain_id:>10}  {chain.chain_name}")

        # Quote + build a cross-chain order: 10 USDC on Base -> USDC on Arbitrum.
        order = client.create_order(
            src_chain_id=ChainId.BASE,
            src_chain_token_in=BASE_USDC,
            src_chain_token_in_amount="10000000",  # 10 USDC (6 decimals)
            dst_chain_id=ChainId.ARBITRUM,
            dst_chain_token_out=ARBITRUM_USDC,
            dst_chain_token_out_amount="auto",  # let the API quote the output
            dst_chain_token_out_recipient=RECIPIENT,
            sender_address=RECIPIENT,
        )

        out = order.estimation.dst_chain_token_out
        print(f"\nOrder {order.order_id}")
        print(f"  you receive ~{out.amount} of {out.symbol} on Arbitrum")
        print(f"  send tx to {order.tx.to} with value {order.tx.value}")
        print(f"  recommended slippage: {order.estimation.recommended_slippage}")

        # After you sign & broadcast order.tx, poll the on-chain order to completion:
        #   final = client.poll_status(order.order_id, interval=5, timeout=600)
        #   print(final.status)


if __name__ == "__main__":
    main()
