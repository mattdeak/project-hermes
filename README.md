# project-hermes

A project for high-speed trading across crypto-currency exchanges. Currently, simple triangular arbitrage is the only implemented strategy, though more are in the works. This actually made me some money before they introduced heavy rate limits (which, fair enough).
Currently only supports NDAX, more exchanges to be added. Until then, though, implementing an exchange to work with the arbitrage bot is quite simple, just mimic the design pattern in NDAXSession and NDAXRouter to correspond more closely to the target exchange.

This works fine for NDAX, and could easily be extended to other platforms. However, I got bored and am not going to be developing this further. Do with it what you will.
