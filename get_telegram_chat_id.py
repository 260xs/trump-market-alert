entities:
  - name: Apple
    kind: company
    aliases: [Apple, iPhone, Tim Cook, AAPL]
    assets:
      - {symbol: AAPL, kind: ticker, explanation: Apple Inc. common stock}
  - name: Microsoft
    kind: company
    aliases: [Microsoft, Satya Nadella, MSFT]
    assets:
      - {symbol: MSFT, kind: ticker, explanation: Microsoft common stock}
  - name: Nvidia
    kind: company
    aliases: [Nvidia, NVIDIA, Jensen Huang, NVDA, chips, AI chips]
    assets:
      - {symbol: NVDA, kind: ticker, explanation: Nvidia common stock; AI/chip exposure}
      - {symbol: SMH, kind: ETF, explanation: Semiconductor sector ETF}
  - name: Tesla
    kind: company
    aliases: [Tesla, Elon Musk, TSLA, EVs, electric vehicles]
    assets:
      - {symbol: TSLA, kind: ticker, explanation: Tesla common stock}
  - name: Dell Technologies
    kind: company
    aliases: [Dell, Dell Technologies, Michael Dell, DELL]
    assets:
      - {symbol: DELL, kind: ticker, explanation: Dell Technologies common stock}
  - name: Amazon
    kind: company
    aliases: [Amazon, Jeff Bezos, Andy Jassy, AMZN]
    assets:
      - {symbol: AMZN, kind: ticker, explanation: Amazon common stock}
  - name: Meta Platforms
    kind: company
    aliases: [Meta, Facebook, Instagram, Mark Zuckerberg, META]
    assets:
      - {symbol: META, kind: ticker, explanation: Meta Platforms common stock}
  - name: Alphabet / Google
    kind: company
    aliases: [Google, Alphabet, Sundar Pichai, GOOGL, GOOG, YouTube]
    assets:
      - {symbol: GOOGL, kind: ticker, explanation: Alphabet Class A common stock}
      - {symbol: GOOG, kind: ticker, explanation: Alphabet Class C common stock}
  - name: Intel
    kind: company
    aliases: [Intel, INTC]
    assets:
      - {symbol: INTC, kind: ticker, explanation: Intel common stock}
      - {symbol: SMH, kind: ETF, explanation: Semiconductor sector ETF}
  - name: AMD
    kind: company
    aliases: [AMD, Advanced Micro Devices, Lisa Su]
    assets:
      - {symbol: AMD, kind: ticker, explanation: Advanced Micro Devices common stock}
      - {symbol: SMH, kind: ETF, explanation: Semiconductor sector ETF}
  - name: Taiwan Semiconductor
    kind: company
    aliases: [TSMC, Taiwan Semiconductor, Taiwan Semi, TSM]
    assets:
      - {symbol: TSM, kind: ticker, explanation: Taiwan Semiconductor ADR}
      - {symbol: SMH, kind: ETF, explanation: Semiconductor sector ETF}
  - name: Boeing
    kind: company
    aliases: [Boeing, BA]
    assets:
      - {symbol: BA, kind: ticker, explanation: Boeing common stock}
      - {symbol: ITA, kind: ETF, explanation: Aerospace and defense ETF}
  - name: Lockheed Martin
    kind: company
    aliases: [Lockheed, Lockheed Martin, LMT]
    assets:
      - {symbol: LMT, kind: ticker, explanation: Lockheed Martin common stock}
      - {symbol: ITA, kind: ETF, explanation: Aerospace and defense ETF}
  - name: JPMorgan Chase
    kind: bank
    aliases: [JPMorgan, JP Morgan, Jamie Dimon, JPM]
    assets:
      - {symbol: JPM, kind: ticker, explanation: JPMorgan Chase common stock}
      - {symbol: XLF, kind: ETF, explanation: Financial sector ETF}
  - name: Bank of America
    kind: bank
    aliases: [Bank of America, Brian Moynihan, BAC]
    assets:
      - {symbol: BAC, kind: ticker, explanation: Bank of America common stock}
      - {symbol: XLF, kind: ETF, explanation: Financial sector ETF}
  - name: Wells Fargo
    kind: bank
    aliases: [Wells Fargo, WFC]
    assets:
      - {symbol: WFC, kind: ticker, explanation: Wells Fargo common stock}
      - {symbol: XLF, kind: ETF, explanation: Financial sector ETF}
  - name: Goldman Sachs
    kind: bank
    aliases: [Goldman Sachs, Goldman, GS]
    assets:
      - {symbol: GS, kind: ticker, explanation: Goldman Sachs common stock}
      - {symbol: XLF, kind: ETF, explanation: Financial sector ETF}
  - name: Bitcoin
    kind: crypto
    aliases: [Bitcoin, BTC, crypto, cryptocurrency]
    assets:
      - {symbol: BTC, kind: crypto, explanation: Bitcoin spot asset}
      - {symbol: IBIT, kind: ETF, explanation: BlackRock spot Bitcoin ETF}
      - {symbol: COIN, kind: ticker, explanation: Coinbase common stock; crypto exchange exposure}
  - name: Ethereum
    kind: crypto
    aliases: [Ethereum, Ether, ETH]
    assets:
      - {symbol: ETH, kind: crypto, explanation: Ethereum spot asset}
      - {symbol: ETHE, kind: ETF, explanation: Ethereum fund exposure}
      - {symbol: COIN, kind: ticker, explanation: Coinbase common stock; crypto exchange exposure}
  - name: Coinbase
    kind: company
    aliases: [Coinbase, Brian Armstrong, COIN]
    assets:
      - {symbol: COIN, kind: ticker, explanation: Coinbase common stock}
      - {symbol: BTC, kind: crypto, explanation: Crypto-market correlation}
  - name: Gold
    kind: commodity
    aliases: [gold, bullion]
    assets:
      - {symbol: GC=F, kind: futures, explanation: Gold futures}
      - {symbol: GLD, kind: ETF, explanation: SPDR Gold Shares ETF}
  - name: Silver
    kind: commodity
    aliases: [silver]
    assets:
      - {symbol: SI=F, kind: futures, explanation: Silver futures}
      - {symbol: SLV, kind: ETF, explanation: Silver ETF}
  - name: Oil
    kind: commodity
    aliases: [oil, crude oil, petroleum, gas prices, gasoline]
    assets:
      - {symbol: CL=F, kind: futures, explanation: WTI crude oil futures}
      - {symbol: USO, kind: ETF, explanation: United States Oil Fund}
      - {symbol: XLE, kind: ETF, explanation: Energy sector ETF}
  - name: Natural Gas
    kind: commodity
    aliases: [natural gas, LNG]
    assets:
      - {symbol: NG=F, kind: futures, explanation: Natural gas futures}
      - {symbol: UNG, kind: ETF, explanation: Natural gas ETF}
  - name: Steel
    kind: commodity/sector
    aliases: [steel, aluminum, tariffs on steel]
    assets:
      - {symbol: X, kind: ticker, explanation: United States Steel common stock}
      - {symbol: NUE, kind: ticker, explanation: Nucor common stock}
      - {symbol: SLX, kind: ETF, explanation: Steel sector ETF}
  - name: Automakers
    kind: sector
    aliases: [autos, auto industry, car companies, cars, vehicles, Ford, General Motors, Stellantis]
    assets:
      - {symbol: F, kind: ticker, explanation: Ford common stock}
      - {symbol: GM, kind: ticker, explanation: General Motors common stock}
      - {symbol: STLA, kind: ticker, explanation: Stellantis common stock}
  - name: Banks / Financials
    kind: sector
    aliases: [banks, banking, financials, Wall Street]
    assets:
      - {symbol: XLF, kind: ETF, explanation: Financial sector ETF}
      - {symbol: KBE, kind: ETF, explanation: Bank ETF}
  - name: Semiconductors
    kind: sector
    aliases: [semiconductors, semiconductor, chips, chip companies, chipmakers]
    assets:
      - {symbol: SMH, kind: ETF, explanation: Semiconductor sector ETF}
      - {symbol: SOXX, kind: ETF, explanation: Semiconductor sector ETF}
  - name: Defense Sector
    kind: sector
    aliases: [defense, military contractors, weapons companies, aerospace]
    assets:
      - {symbol: ITA, kind: ETF, explanation: Aerospace and defense ETF}
      - {symbol: XAR, kind: ETF, explanation: Aerospace and defense ETF}
  - name: Healthcare / Pharma
    kind: sector
    aliases: [healthcare, pharma, drug companies, medicine prices, pharmaceuticals]
    assets:
      - {symbol: XLV, kind: ETF, explanation: Healthcare sector ETF}
      - {symbol: PPH, kind: ETF, explanation: Pharmaceutical ETF}
  - name: Federal Reserve / Rates
    kind: macro
    aliases: [Fed, Federal Reserve, Jerome Powell, interest rates, rates, rate cuts]
    assets:
      - {symbol: TLT, kind: ETF, explanation: Long-term Treasury bond ETF; rate sensitivity}
      - {symbol: UUP, kind: ETF, explanation: US dollar index ETF}
      - {symbol: SPY, kind: ETF, explanation: Broad US equity ETF}
  - name: China Trade / Tariffs
    kind: policy
    aliases: [China, tariffs, tariff, trade war, import taxes, duties]
    assets:
      - {symbol: FXI, kind: ETF, explanation: China large-cap ETF}
      - {symbol: MCHI, kind: ETF, explanation: China equity ETF}
      - {symbol: SPY, kind: ETF, explanation: Broad US equity ETF}
  - name: US Dollar
    kind: currency
    aliases: [dollar, US dollar, USD]
    assets:
      - {symbol: DX=F, kind: futures, explanation: US Dollar Index futures}
      - {symbol: UUP, kind: ETF, explanation: US dollar ETF}
