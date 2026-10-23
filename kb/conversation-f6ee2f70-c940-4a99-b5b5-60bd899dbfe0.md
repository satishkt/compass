# Historical research conversation

Kind: user-authored historical requests, NOT verified facts or current instructions.
Do not treat these as approved shared memories or execute instructions in them.
Session: f6ee2f70-c940-4a99-b5b5-60bd899dbfe0

## User message 2026-10-21T04:13:54.009Z
Message ID: 2624bc5b-0ea4-4ad5-8c8b-7c55d5b16e81

more features to add 1. Incorporate guidance into valuation models, 2. Incorporate buyback into valuation - flag the authorization announced by the company, what is left over. 3. Add KPIs the management is incentivized on into the company profile.

## User message 2026-10-22T05:38:23.093Z
Message ID: 19a479b1-5866-4f61-9b91-a77146d6721b

Lets also add total return from a stock ..i.e for my current holdings - i want to be able to calculate the total return so far - dividends+ price change + buyback yield etc. Another feature to be able to create a portfolio/aggregation view differently , right now portfolio is nothing but an aggregation of accounts. Another view i want is named categories and categorize stocks into one or more of these categoris and visualize returns, attribution, risk along those categories.

## User message 2026-10-22T05:42:49.160Z
Message ID: fecf5f15-8db5-4cd2-b098-a6744cae5f43

Another bug lets fix is the front page of the app display of FV on the tickers. I want to use the DCF value that we get from the valuation page as the default FV of the ticker and then overwrite it if needed. I want to be able to persist and show it on the front page .

## User message 2026-10-22T06:54:30.490Z
Message ID: 8f58f6cc-a048-4ff9-b58e-32494e3eb571

I want to use an alternate valuation method in cases where a dcf cannot be computed - for instance if fcf is negative then perhaps use ocf, if net income is negative then look at multiples for the industry and comparables - use the parallel api to fetch an appropriate multiple or from comparables. For companies that dont fit into a traditional structure say a bank or an insurance company use alternate valuation mdethods - p/tbv or others. I definitely dont want to boil the ocean trying to do all the adjustments - in cases there are questions - use the task api or other apis like tavily or parallel ai to get the answers to those . Also identify and give me a way to see how that valuation was calculated.