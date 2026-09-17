# Desktop Store

Offline shop software for one computer or one phone. No internet after install. No demo data.

On first open the store is empty. You register the shop name and your own username and password. Only then is anything written to the database.

## Termux (this phone hosts the shop)

In Termux paste:

```
curl -fsSL https://raw.githubusercontent.com/Quantikz/desktop-store/main/termux-setup.sh | bash
```

Then open `http://127.0.0.1:8080` on that phone. Other phones on the same Wi‑Fi use the address shown in Termux. Next time run `desktop-store`.

Leave Termux open while the shop is in use.

## Windows program

Download **DesktopStore-Windows.zip** from Releases.

1. Unzip the folder onto the store PC.
2. Double-click **Start Desktop Store**.
3. Register the store. Choose your own name and password.
4. Home shows **This computer** and **Phones on this Wi‑Fi**.

## What it does

- Register the store on first use (no default user, no default password)
- Add products with selling price, buying cost, stock and photo
- Sell at the till (cash, transfer or card)
- Performance: sales, cost of stock sold, profit, stock value
- Everything stays in a local SQLite file on that device
