"""Async quickstart: list chains and quote an EVM->Solana order concurrently."""

import asyncio

from debridge import AsyncDebridgeClient
from debridge.constants import ChainId

BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
SOLANA_USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOLANA_RECIPIENT = "GZ1WYUw1z7Z1cBNFA8e3y6PUuRDHWfp8a8Z9pdEhmTbE"
EVM_SENDER = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"


async def main() -> None:
    async with AsyncDebridgeClient() as client:
        chains, order = await asyncio.gather(
            client.get_supported_chains(),
            client.create_order(
                src_chain_id=ChainId.BASE,
                src_chain_token_in=BASE_USDC,
                src_chain_token_in_amount="10000000",
                dst_chain_id=ChainId.SOLANA,
                dst_chain_token_out=SOLANA_USDC,
                dst_chain_token_out_recipient=SOLANA_RECIPIENT,
                sender_address=EVM_SENDER,
            ),
        )
        print(f"{len(chains.chains)} chains supported")
        out = order.estimation.dst_chain_token_out
        print(f"Order {order.order_id}: ~{out.amount} {out.symbol} to Solana")


if __name__ == "__main__":
    asyncio.run(main())
