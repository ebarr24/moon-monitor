# Moon Monitor - pump.fun Token Tracker

A real-time token monitoring application for Solana, featuring:
- Live token tracking and growth analysis
- Automated trading capabilities
- Multi-wallet management (soonish)
- Real-time price updates and market cap tracking
- Beautiful, responsive UI with dark mode

## Prerequisites

- [Node.js](https://nodejs.org/) (v16 or higher)
- [Python](https://www.python.org/) (v3.8 or higher)
- Windows OS (for running the batch file directly)

## Quick Start

1. Download the latest release from the [Releases](https://github.com/ebarr24/moon-monitor/releases) page
2. Extract the zip file to your desired location
3. Double-click `run.bat`
4. Wait for the installation process to complete
5. Access the application at:
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8000

The batch file will automatically:
- Create a Python virtual environment
- Install Python dependencies
- Install Node.js dependencies
- Start both the backend and frontend servers

## Manual Setup

If you prefer to set up manually or are using a different OS:

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Configuration

### Wallet Management
1. Access the wallet management panel through the UI
2. Add your wallet details:
   - Public Key
   - Private Key
   - API Key (optional)
   - Pool selection

### Trading Settings
- Adjust slippage tolerance
- Set priority fees
- Enable/disable trading mode

## Security

- All sensitive data is stored locally in the `backend/secure` directory
- Private keys are never transmitted to external services
- API keys are required for trading functionality

## Support

For issues and feature requests, please [open an issue](https://github.com/yourusername/moon-monitor/issues)

## License

MIT License - See LICENSE file for details 