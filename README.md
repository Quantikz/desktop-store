# Desktop Store

Offline shop software for one Windows computer. Python + SQLite. No internet. No demo data.

On first open the store is empty. You register the shop name and your own username and password. Only then is anything written to the database on this PC.

## What it does

- Register the store on first use (no default user, no default password)
- Add products with selling price, buying cost, stock and photo
- Sell at the till (cash, transfer or card)
- Stock falls when a sale is saved
- Performance: sales, cost of stock sold, profit, stock value
- Staff accounts you create yourself
- Everything stays in a local SQLite file on this computer

## Run from source

```
pip install -r requirements.txt
python run.py
```

## Windows program

Download **DesktopStore-Windows.zip** from Releases.

1. Unzip the folder onto the store PC.
2. Double-click **Start Desktop Store**.
3. Register the store. Choose your own name and password.
4. Add products, then sell.

The shop book is saved at:

`C:\Users\<name>\AppData\Roaming\DesktopStore\store.db`

There are no sample products and no PIN 1234.
