# project-hermes

A project for high-speed trading across crypto-currency exchanges. Currently, simple triangular arbitrage is the only implemented strategy, though more are in the works.
Currently only supports NDAX, more exchanges to be added. Until then, though, implementing an exchange to work with the arbitrage bot is quite simple, just override the design pattern in NDAXSession and NDAXRouter to correspond more closely to the target exchange.

This library is still WIP, and some things may be refactored in the future.
