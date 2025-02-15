<template>
  <div class="container">
    <div class="main-content">
      <div class="content-wrapper">
        <div class="header">
          <div class="title-section">
            <h1>Moon Monitor</h1>
            <div class="info-tooltip">
              <span class="info-icon">ℹ️</span>
              <div class="tooltip-content">
                {{ trackingCriteriaDescription }}
              </div>
            </div>
          </div>
          <div class="status-section">
            <div class="connection-status" :class="{ connected: isConnected }">
              {{ isConnected ? 'Connected' : 'Disconnected' }}
            </div>
            <div class="token-count">
              {{ Object.keys(tokens).length }} tokens tracked
            </div>
            <div class="trading-controls">
              <button class="trading-mode-button" @click="showWalletModal = true">
                Wallets ({{ walletStatus.active_wallets }})
              </button>
              <button class="trading-mode-button" :class="{ active: tradingEnabled }" @click="toggleTradingMode">
                {{ tradingEnabled ? 'Trading On' : 'Trading Off' }}
              </button>
            </div>
            <button class="reset-button" @click="resetData">Reset</button>
          </div>
        </div>

        <div class="token-container">
          <div class="token-list">
            <div v-for="token in sortedTokens" :key="token.mint" class="token-card">
              <div class="token-header">
                <div class="token-title">
                  <h3>
                    <span class="token-symbol">${{ token.symbol }}</span>
                    <a style="padding-left: 5px;" :href="'https://pump.fun/coin/' + token.mint" target="_blank">
                      {{ truncateName(token.name) }}
                    </a>
                  </h3>
                </div>
                <div class="token-time">{{ getTimeAgo(token.timestamp) }}</div>
              </div>

              <div class="metrics-row">
                <div class="growth-rate-section" :style="getGrowthRateStyle(token.growthRate)">
                  <div class="metric-label">Growth Rate</div>
                  <div class="growth-value">
                    {{ formatGrowthScore(token.growthRate) }}
                  </div>
                </div>

                <div class="market-cap">
                  <div class="metric-label">Market Cap</div>
                  <div class="metric-value">
                    {{ formatSolLong(token.marketCapSol) }} SOL
                    <div class="usd-value">${{ formatUsd(token.marketCapSol * solPrice) }}</div>
                  </div>
                </div>
              </div>

              <div class="token-metrics">
                <div class="metric">
                  <div class="metric-label">Token Price</div>
                  <div class="metric-value">
                    {{ formatSolPrice(token.marketCapSol / 1000000000) }} SOL
                    <div class="usd-value">
                      ${{ formatTokenPrice((token.marketCapSol * solPrice) / 1000000000) }}
                    </div>
                  </div>
                </div>
              </div>

              <div class="token-links">
                <div class="link-item">
                  <span class="link-label">Contract:</span>
                  <a :href="'https://solscan.io/token/' + token.mint" target="_blank" class="address-link">
                    {{ truncateAddress(token.mint) }}
                    <span class="external-link">↗</span>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="high-growth-sidebar">
        <div class="sidebar-header">
          <h2>High Growth Tokens</h2>
          <div class="net-percentage" :class="{ 'positive': netPercentageGain > 0, 'negative': netPercentageGain < 0 }">
            {{ netPercentageGain > 0 ? '+' : '' }}{{ netPercentageGain.toFixed(2) }}% total
          </div>
        </div>
        <div class="high-growth-list">
          <div v-for="token in sortedHighGrowthTokens" 
               :key="token.mint" 
               class="high-growth-card"
               :class="{
                 'waiting': !token.hasStartedTracking,
                 'positive-glow': !token.exitPrice && token.currentPrice > token.entryPrice && token.hasStartedTracking,
                 'negative-glow': !token.exitPrice && token.currentPrice < token.entryPrice && token.hasStartedTracking,
                 'exited-positive': token.exitPrice && token.exitPrice > token.entryPrice,
                 'exited-negative': token.exitPrice && token.exitPrice < token.entryPrice,
                 'trading-enabled': tradingEnabled && !token.exitPrice && !token.entryTx
               }">
            <div class="high-growth-title">
              <h3>
                <a :href="'https://pump.fun/coin/' + token.mint" target="_blank">
                  {{ truncateName(token.name) }}
                </a>
              </h3>
              <div class="growth-stats">
                <div v-if="!token.hasStartedTracking" class="countdown-badge">
                  {{ Math.max(0, Math.ceil((3000 - (Date.now() - token.potentialEntryTime)) / 1000)) }}s
                </div>
                <div v-if="token.hasStartedTracking" class="growth-badge">{{ formatGrowthScore(token.averageGrowth) }} avg</div>
                <div v-if="token.hasStartedTracking" class="time-badge">
                  {{ formatDuration(token.timestamp, token.exitPrice ? (token.exitTime || Date.now()) : Date.now()) }}
                </div>
                <div v-if="tradingEnabled && !token.exitPrice && !token.entryTx" class="trading-badge">
                  Trading
                </div>
              </div>
            </div>
            <div class="price-metrics">
              <div v-if="!token.hasStartedTracking" class="price-row">
                <span class="price-label">Potential Entry:</span>
                <span class="price-value">${{ formatTokenPrice(token.potentialEntryPrice) }}</span>
              </div>
              <div v-if="!token.hasStartedTracking" class="price-row">
                <span class="price-label">Current:</span>
                <span class="price-value" :class="{
                  'positive-value': token.currentPrice >= token.potentialEntryPrice,
                  'negative-value': token.currentPrice < token.potentialEntryPrice
                }">${{ formatTokenPrice(token.currentPrice) }}</span>
              </div>
              <div v-if="token.hasStartedTracking" class="price-row">
                <span class="price-label">Entry:</span>
                <span class="price-value">${{ formatTokenPrice(token.entryPrice) }}</span>
              </div>
              <div v-if="token.hasStartedTracking && !token.exitPrice" class="price-row">
                <span class="price-label">Current:</span>
                <span class="price-value" :class="{
                  'positive-value': token.currentPrice > token.entryPrice,
                  'negative-value': token.currentPrice < token.entryPrice
                }">${{ formatTokenPrice(token.currentPrice) }}</span>
              </div>
              <div v-if="token.hasStartedTracking && !token.exitPrice" class="live-gain">
                <div class="status-chips">
                  <div class="active-chip">Active</div>
                  <button class="close-button" @click="manualExitPosition(token)">Close</button>
                  <button v-if="tradingEnabled && !token.entryTx" 
                          class="trade-button" 
                          @click="manualEntryTrade(token)"
                          :disabled="walletStatus.active_wallets === 0">
                    Trade
                  </button>
                </div>
                <div :class="{
                  'positive': token.currentPrice > token.entryPrice,
                  'negative': token.currentPrice < token.entryPrice
                }">
                  {{ ((token.currentPrice - token.entryPrice) / token.entryPrice * 100).toFixed(2) }}%
                </div>
              </div>
              <div v-if="token.exitPrice" class="price-row">
                <span class="price-label">Exit:</span>
                <span class="price-value" :class="{
                  'positive-value': token.exitPrice > token.entryPrice,
                  'negative-value': token.exitPrice < token.entryPrice
                }">${{ formatTokenPrice(token.exitPrice) }}</span>
              </div>
              <div v-if="token.exitPrice" class="total-gain" :class="{ 'positive': token.percentageGain > 0 }">
                {{ token.percentageGain > 0 ? '+' : '' }}{{ token.percentageGain.toFixed(2) }}%
              </div>
              <div v-if="token.entryTx || token.exitTx" class="trade-links">
                <div v-if="token.entryTx" class="trade-link">
                  <a :href="'https://solscan.io/tx/' + token.entryTx" target="_blank" class="transaction-link">
                    Entry Tx <span class="external-link">↗</span>
                  </a>
                  <div class="trade-wallet">{{ truncateAddress(token.entryWallet) }}</div>
            </div>
                <div v-if="token.exitTx" class="trade-link">
                  <a :href="'https://solscan.io/tx/' + token.exitTx" target="_blank" class="transaction-link">
                    Exit Tx <span class="external-link">↗</span>
                  </a>
          </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Debug Console -->
    <div class="debug-console" :class="{ 'expanded': isDebugExpanded }">
      <div class="debug-header" @click="toggleDebugConsole">
        Debug Console
        <span class="expand-icon">{{ isDebugExpanded ? '▼' : '▲' }}</span>
      </div>
      <div v-if="isDebugExpanded" class="debug-content">
        <div class="debug-filters">
          <label>
            <input type="checkbox" v-model="debugFilters.trades" /> Show Trades
          </label>
          <label>
            <input type="checkbox" v-model="debugFilters.errors" /> Show Errors
          </label>
          <label>
            <input type="checkbox" v-model="debugFilters.wallet" /> Show Wallet Updates
          </label>
          <label>
            <input type="checkbox" v-model="debugFilters.exits" /> Show Position Exits
          </label>
          <button class="clear-logs" @click="clearLogs">Clear</button>
        </div>
        <div class="log-container">
          <div v-for="log in filteredLogs" 
               :key="log.timestamp" 
               class="log-entry"
               :class="log.type">
            <span class="log-time">{{ formatTime(log.timestamp) }}</span>
            <span class="log-message">{{ log.message }}</span>
            <a v-if="log.type === 'trade' && log.txSignature" 
               :href="'https://solscan.io/tx/' + log.txSignature" 
               target="_blank" 
               class="transaction-link">
              View Transaction <span class="external-link">↗</span>
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Wallet Management Modal -->
    <div v-if="showWalletModal" class="modal-overlay">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Wallet Management</h2>
          <button class="close-modal" @click="showWalletModal = false">&times;</button>
        </div>
        
        <div class="wallet-settings">
          <h3>Global Settings</h3>
          <div class="settings-row">
            <label>
              Slippage (%):
              <input type="number" v-model="globalSlippage" @change="updateGlobalSettings" min="0" max="100" step="0.1">
            </label>
            <label>
              Priority Fee (SOL):
              <input type="number" v-model="globalPriorityFee" @change="updateGlobalSettings" min="0" step="0.0001">
            </label>
          </div>
        </div>

        <div class="wallet-list">
          <h3>Connected Wallets</h3>
          <div class="wallet-summary">
            <div class="wallet-count">{{ walletStatus.active_wallets }} Active Wallets</div>
            <div v-if="walletStatus.total_sol" class="wallet-balance">
              Total Balance: {{ formatSol(walletStatus.total_sol) }} SOL
              <span v-if="solPrice" class="usd-value">
                (${{ formatUsd(walletStatus.total_sol * solPrice) }})
              </span>
            </div>
          </div>
          <div v-for="wallet in wallets" :key="wallet.public_key" class="wallet-item">
            <div class="wallet-info">
              <div class="wallet-address">{{ truncateAddress(wallet.public_key) }}</div>
              <div class="wallet-details">
                <span class="pool-info">{{ wallet.pool }}</span>
                <span v-if="wallet.balance" class="wallet-balance">
                  {{ formatSol(wallet.balance) }} SOL
                  <span v-if="solPrice" class="usd-value">
                    (${{ formatUsd(wallet.balance * solPrice) }})
                  </span>
                </span>
                <span class="last-used" v-if="wallet.last_used">
                  Last used: {{ formatTime(new Date(wallet.last_used).getTime()) }}
                </span>
              </div>
            </div>
            <button 
              class="remove-wallet" 
              @click="removeWallet(wallet.public_key)"
              :disabled="isRemovingWallet === wallet.public_key">
              <span v-if="isRemovingWallet === wallet.public_key" class="loading-spinner"></span>
              <span v-else>Remove</span>
            </button>
          </div>
        </div>

        <div class="add-wallet-form">
          <h3>Add New Wallet</h3>
          <div class="form-row">
            <input type="text" v-model="newWallet.publicKey" placeholder="Public Key">
          </div>
          <div class="form-row">
            <input type="password" v-model="newWallet.privateKey" placeholder="Private Key">
          </div>
          <div class="form-row">
            <input type="password" v-model="newWallet.apiKey" placeholder="API Key (Optional)">
          </div>
          <div class="form-row">
            <select v-model="newWallet.pool">
              <option value="pump">Pump</option>
              <option value="raydium">Raydium</option>
              <option value="auto">Auto</option>
            </select>
          </div>
          <button 
            class="add-wallet-button" 
            @click="addWallet" 
            :disabled="isAddingWallet || !newWallet.publicKey || !newWallet.privateKey">
            {{ isAddingWallet ? 'Adding...' : 'Add Wallet' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const tokens = ref({})
const isConnected = ref(false)
const logs = ref([])
const solPrice = ref(0)
const highGrowthTokens = ref({})
let ws = null
let priceInterval = null
let timeInterval = null
let cullInterval = null
let growthCheckInterval = null
let walletStatusInterval = null
const forceUpdate = ref(0)

const showWalletModal = ref(false)
const tradingEnabled = ref(localStorage.getItem('tradingEnabled') === 'true')
const testMode = ref(true)
const walletStatus = ref({
  active_wallets: 0,
  total_wallets: 0,
  trading_enabled: false,
  test_mode: true
})
const newWallet = ref({
  publicKey: '',
  privateKey: '',
  apiKey: '',
  pool: 'pump'
})
const wallets = ref([])
const isAddingWallet = ref(false)
const isRemovingWallet = ref(null)
const globalSlippage = ref(5)  // Default 5%
const globalPriorityFee = ref(0.005)  // Default 0.005 SOL

// Debug console state
const isDebugExpanded = ref(true)
const debugFilters = ref({
  trades: true,
  errors: true,
  wallet: true,
  exits: true
})

// Add computed for current time that updates with forceUpdate
const currentTime = computed(() => {
  forceUpdate.value // depend on forceUpdate to trigger reactivity
  return Date.now()
})

const calculateTradeActivityScore = (trades, currentTime) => {
  const DECAY_FACTOR = 0.25 // Increased from 0.1 to make trades decay faster
  const EARLY_TRADE_WEIGHT = 0.25 // Early trades have 25% of normal impact
  
  return trades.reduce((score, trade) => {
    const timeDiff = (currentTime - trade.timestamp) / 1000 // Convert to seconds
    const timeDecay = Math.exp(-DECAY_FACTOR * timeDiff)
    const tradeImpact = trade.type === 'buy' ? 1 : -1
    
    // Apply reduced weight for early trades
    const weight = trade.isEarlyTrade ? EARLY_TRADE_WEIGHT : 1
    
    return score + (tradeImpact * timeDecay * weight)
  }, 0)
}

// Calculate growth rate for a single token
const calculateGrowthRate = (token) => {
  const timeSinceCreation = (currentTime.value - token.timestamp) / 1000
  // Calculate base market cap growth rate
  const marketCapChange = token.marketCapSol - token.initialMarketCap
  const baseGrowthRate = marketCapChange / Math.max(timeSinceCreation, 0.001)
  
  // Calculate trade activity score
  const tradeActivityScore = calculateTradeActivityScore(token.trades || [], currentTime.value)
  
  // Combine the metrics
  // We use Math.max to ensure the score doesn't go negative, and add 1 to tradeActivityScore
  // to make it a multiplier that's always positive
  return baseGrowthRate * Math.max(0, 1 + tradeActivityScore)
}

// Track when tokens go negative
const updateNegativeGrowthTracking = (token, growthRate) => {
  if (growthRate < 1) {  // Changed from 0 to 1
    // If token just went below threshold, record the timestamp
    if (!token.negativeGrowthSince) {
      token.negativeGrowthSince = Date.now()
    }
  } else {
    // Reset tracking if token goes above threshold
    if (token.negativeGrowthSince) {
      delete token.negativeGrowthSince
    }
  }
}

// Cull dead tokens
const cullDeadTokens = () => {
  const currentTime = Date.now()
  const deadTokens = []
  
  Object.entries(tokens.value).forEach(([mint, token]) => {
    if (token.negativeGrowthSince && (currentTime - token.negativeGrowthSince) > 30000) {
      deadTokens.push({ mint, name: token.name })
      delete tokens.value[mint]
    }
  })
  
  if (deadTokens.length > 0) {
    deadTokens.forEach(token => {
      addLog(`Removed inactive token: ${token.name} (below threshold for >30s)`, 'info')
    })
  }
}

const sortedTokens = computed(() => {
  return Object.values(tokens.value)
    .map(token => {
      const growthRate = calculateGrowthRate(token)
      // Update negative growth tracking
      updateNegativeGrowthTracking(token, growthRate)
      return {
        ...token,
        growthRate
      }
    })
    .sort((a, b) => b.growthRate - a.growthRate)
    .slice(0, 6)
})

const fetchSolPrice = async () => {
  try {
    const response = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd')
    const data = await response.json()
    solPrice.value = data.solana.usd
    addLog(`Updated SOL price: $${solPrice.value}`)
  } catch (error) {
    addLog(`Error fetching SOL price: ${error}`, 'error')
  }
}

const addLog = (message, type = 'info', txSignature = null) => {
  // Skip inactive token messages
  if (message.includes('below threshold for >30s')) {
    return
  }
  
  // Convert token updates to 'trade' type for proper filtering
  if (message.includes('Update for') && message.includes('SOL')) {
    type = 'trade'
  }
  
  logs.value.unshift({
    timestamp: Date.now(),
    message,
    type,
    txSignature
  })
  
  if (logs.value.length > 100) {
    logs.value = logs.value.slice(0, 100)
  }
  
  console.log(`[${type}] ${message}`)
}

const resetData = () => {
  tokens.value = {}
  highGrowthTokens.value = {}
  logs.value = []
  addLog('Data reset', 'info')
}

const connectWebSocket = () => {
  addLog('Connecting to WebSocket...', 'info')
  ws = new WebSocket('ws://localhost:8000/ws')
  
  ws.onopen = () => {
    isConnected.value = true
    addLog('Connected to WebSocket', 'success')
  }
  
  ws.onclose = (event) => {
    isConnected.value = false
    addLog(`Disconnected from WebSocket (code: ${event.code}). Attempting to reconnect in 5s...`, 'error')
    setTimeout(connectWebSocket, 5000)
  }

  ws.onerror = (error) => {
    addLog(`WebSocket error: ${error}`, 'error')
  }
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      
      if (data.type === 'token_update') {
        const tokenData = data.data
        const msgType = tokenData.txType || 'unknown'

        if (msgType === 'create' && tokenData.mint && !tokens.value[tokenData.mint]) {
          // Add debug logging for price calculation
          const priceInUsd = (tokenData.marketCapSol * solPrice.value) / (tokenData.supply || 1000000000)
          console.debug('Token price calculation:', {
            marketCapSol: tokenData.marketCapSol,
            solPrice: solPrice.value,
            supply: tokenData.supply || 1000000000,
            calculatedPrice: priceInUsd
          })
          
          // Log formatted token info
          console.log('🆕 New Token Created:', {
            name: tokenData.name,
            symbol: tokenData.symbol,
            marketCap: `${tokenData.marketCapSol} SOL`,
            price: `$${formatTokenPrice(priceInUsd)}`,
            mint: tokenData.mint,
            solAmount: `${tokenData.solAmount} SOL`,
            timestamp: new Date().toISOString(),
            creator: tokenData.creator || 'Unknown'
          })
          
          // Debug log of all raw data
          console.log('Raw token data:', tokenData)
          
          // Store initial values when first seeing a token
          tokenData.timestamp = Date.now()
          tokenData.initialMarketCap = tokenData.marketCapSol || 0
          tokenData.trades = tokenData.trades || []
          tokens.value[tokenData.mint] = tokenData
          addLog(`New token: ${tokenData.name} (${tokenData.symbol})`, 'success')
        } else if ((msgType === 'buy' || msgType === 'sell' || msgType === 'update') && tokenData.mint && tokens.value[tokenData.mint]) {
          // Update token data while preserving initial values and tracking trades
          const token = tokens.value[tokenData.mint]
          const initialValues = {
            timestamp: token.timestamp,
            initialMarketCap: token.initialMarketCap,
            trades: tokenData.trades || token.trades || []  // Use new trades array if provided, fallback to existing
          }
          tokens.value[tokenData.mint] = {
            ...tokenData,
            ...initialValues
          }
          addLog(`Update for ${token.name}: ${msgType} ${tokenData.solAmount || ''} SOL`, 'info')
        }
      }
    } catch (error) {
      console.error('Message processing error:', error)
      addLog(`Error processing message: ${error}`, 'error')
    }
  }
}

const formatTime = (timestamp) => {
  return new Date(timestamp).toLocaleTimeString()
}

const truncateAddress = (address) => {
  if (!address) return ''
  return `${address.slice(0, 4)}...${address.slice(-4)}`
}

const formatNumber = (num) => {
  if (!num) return '0'
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2
  }).format(num)
}

const formatSol = (num) => {
  if (!num) return '0'
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3
  }).format(num)
}

const formatUsd = (num) => {
  if (!num) return '0.00'
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num)
}

const getTimeAgo = computed(() => (timestamp) => {
  forceUpdate.value
  if (!timestamp) return ''
  const seconds = Math.floor((Date.now() - timestamp) / 1000)
  
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
})

const truncateName = (name) => {
  if (!name) return ''
  return name.length > 15 ? name.slice(0, 15) + '...' : name
}

const getGrowthRateStyle = (score) => {
  if (score === 0) return {}
  
  let intensity, color
  if (score < 1) {
    // Red glow for scores under 1
    intensity = Math.max(0.1, score)
    const alpha = Math.min(0.5, intensity * 0.5)
    color = `rgba(239, 68, 68, ${alpha})`  // Using red-500 from Tailwind
  } else if (score >= 10) {
    // Green glow for scores 10 and above
    intensity = Math.min(1, (score - 10) / 20) // Normalize to reasonable range
    const alpha = Math.min(0.5, 0.1 + intensity * 0.4)
    color = `rgba(34, 197, 94, ${alpha})`  // Using green-500 from Tailwind
  } else {
    // No glow for scores between 1 and 10
    return {}
  }
  
  return {
    boxShadow: `0 0 20px ${color}`,
    background: `linear-gradient(to bottom, #1e293b, ${color.replace(/, [\d.]+\)/, ', 0.1)')})`
  }
}

const formatGrowthScore = (score) => {
  // Format the growth score with a consistent number of decimal places
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(score)
}

// Add function to check for recent early trades
const hasRecentEarlyTrade = (token) => {
  if (!token.trades || token.trades.length === 0) return false
  
  // Look at trades in the last 10 seconds
  const recentTime = Date.now() - 10000
  return token.trades.some(trade => 
    trade.timestamp > recentTime && trade.isEarlyTrade
  )
}

const formatTokenPrice = (num) => {
  if (!num) return '0.0000000000'
  
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 10,
    maximumFractionDigits: 10,
    useGrouping: true
  }).format(num)
}

const formatSolPrice = (num) => {
  if (!num) return '0.0000000000'
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 10,
    maximumFractionDigits: 10
  }).format(num)
}

const formatSolLong = (num) => {
  if (!num) return '0.00'
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num)
}

// Update the token checking logic
const checkHighGrowthTokens = () => {
  Object.entries(tokens.value).forEach(([mint, token]) => {
    const growthRate = calculateGrowthRate(token)
    const currentPrice = (token.marketCapSol * solPrice.value) / 1000000000
    
    // Only process tokens that haven't been tracked before
    if (!highGrowthTokens.value[mint] || (!highGrowthTokens.value[mint].hasStartedTracking && !highGrowthTokens.value[mint].exitPrice)) {
      // Check if token should be added to high growth tracking
      if (growthRate >= 20) {
        if (!highGrowthTokens.value[mint]) {
          // Initialize tracking
          highGrowthTokens.value[mint] = {
            mint,
            name: token.name,
            potentialEntryPrice: currentPrice,
            potentialEntryTime: Date.now(),
            hasStartedTracking: false,
            initialGrowthRate: growthRate  // Store initial growth rate
          }
        } else if (!highGrowthTokens.value[mint].hasStartedTracking) {
          // Check if it's been above threshold for 3 seconds
          const timeAboveThreshold = Date.now() - highGrowthTokens.value[mint].potentialEntryTime
          
          // Update current price during waiting period
          highGrowthTokens.value[mint].currentPrice = currentPrice
          
          // Cancel if price has dropped below entry price
          if (currentPrice < highGrowthTokens.value[mint].potentialEntryPrice) {
            delete highGrowthTokens.value[mint]
            return
          }
          
          if (timeAboveThreshold >= 3000) {
            // Check if growth rate hasn't decreased by 50% or more
            const growthDecayPercent = (highGrowthTokens.value[mint].initialGrowthRate - growthRate) / highGrowthTokens.value[mint].initialGrowthRate
            
            // Add early high growth check - if growth is too high in first 5s, don't track
            const timeSinceCreation = (Date.now() - token.timestamp) / 1000
            if (timeSinceCreation <= 5 && growthRate > 200) {
              addLog(`Skipping ${token.name} - Growth rate too high (${growthRate.toFixed(2)}) in first 5s`, 'info')
              delete highGrowthTokens.value[mint]
              return
            }
            
            if (growthDecayPercent < 0.5) {  // Less than 50% decay
              // Start actual tracking
              highGrowthTokens.value[mint] = {
                mint,
                name: token.name,
                entryPrice: highGrowthTokens.value[mint].potentialEntryPrice,
                currentPrice: currentPrice,
                currentGrowth: growthRate,
                timestamp: highGrowthTokens.value[mint].potentialEntryTime,
                hasStartedTracking: true,
                growthRates: [growthRate],
                averageGrowth: growthRate,
                sampleCount: 1,
                peakGrowth: growthRate
              }

              // Execute entry trade if trading is enabled
              if (tradingEnabled.value && walletStatus.value.active_wallets > 0) {
                // Find least recently used wallet
                const wallet = wallets.value.reduce((prev, curr) => {
                  if (!prev.last_used) return curr
                  if (!curr.last_used) return prev
                  return new Date(prev.last_used) < new Date(curr.last_used) ? prev : curr
                })

                // Calculate position size (0.1 SOL worth of tokens)
                const positionSizeInSol = 0.1
                
                // Execute buy trade
                executeTrade({
                  mint: mint,
                  action: 'buy',
                  wallet_public_key: wallet.public_key,
                  amount: positionSizeInSol,
                  denominated_in_sol: true
                }).then(result => {
                  addLog(`Entry trade executed for ${token.name}: ${result.signature}`, 'trade')
                  highGrowthTokens.value[mint].entryTx = result.signature
                  highGrowthTokens.value[mint].entryWallet = wallet.public_key
                }).catch(error => {
                  addLog(`Failed to execute entry trade for ${token.name}: ${error}`, 'error')
                })
              }
            } else {
              // Growth decayed too much during waiting period, remove from tracking
              delete highGrowthTokens.value[mint]
            }
          }
        }
      } else {
        // If growth rate drops below threshold during waiting period, remove from tracking
        if (highGrowthTokens.value[mint] && !highGrowthTokens.value[mint].hasStartedTracking) {
          delete highGrowthTokens.value[mint]
        }
      }
    }
    
    // Update existing actively tracked token
    if (highGrowthTokens.value[mint]?.hasStartedTracking && !highGrowthTokens.value[mint].exitPrice) {
      const highGrowthToken = highGrowthTokens.value[mint]
      
      // Update current price and growth
      highGrowthToken.currentPrice = currentPrice
      highGrowthToken.currentGrowth = growthRate
      
      // Update peak growth if current growth is higher
      highGrowthToken.peakGrowth = Math.max(highGrowthToken.peakGrowth, growthRate)
      
      // Update running average
      highGrowthToken.sampleCount++
      const oldAverage = highGrowthToken.averageGrowth
      highGrowthToken.averageGrowth = oldAverage + (growthRate - oldAverage) / highGrowthToken.sampleCount
      highGrowthToken.growthRates.push(growthRate)
      
      // Check for stop loss (-50% from entry price)
      const percentageChange = ((currentPrice - highGrowthToken.entryPrice) / highGrowthToken.entryPrice) * 100
      if (percentageChange <= -50) {
        addLog(`Position Exit: ${token.name} (Stop Loss) ${percentageChange.toFixed(2)}%`, 'exit')
        highGrowthToken.exitPrice = currentPrice
        highGrowthToken.exitTime = Date.now()
        highGrowthToken.percentageGain = percentageChange
        highGrowthToken.finalDecay = (highGrowthToken.peakGrowth - growthRate) / highGrowthToken.peakGrowth
        highGrowthToken.exitReason = 'Stop Loss'

        // Execute exit trade if trading is enabled
        if (tradingEnabled.value && highGrowthToken.entryWallet) {
          executeTrade({
            mint: mint,
            action: 'sell',
            wallet_public_key: highGrowthToken.entryWallet,
            amount: 100,  // Sell 100% of tokens
            denominated_in_sol: false
          }).then(result => {
            addLog(`Exit trade executed for ${token.name}: ${result.signature}`, 'trade')
            highGrowthToken.exitTx = result.signature
          }).catch(error => {
            addLog(`Failed to execute exit trade for ${token.name}: ${error}`, 'error')
          })
        }
        return
      }
      
      // Exit if growth rate drops below 50% of the average
      if (growthRate < (highGrowthToken.averageGrowth * 0.50) && highGrowthToken.sampleCount > 30 && !highGrowthToken.exitPrice) {
        const exitPercent = ((currentPrice - highGrowthToken.entryPrice) / highGrowthToken.entryPrice * 100)
        addLog(`Position Exit: ${token.name} (Growth Decay) ${exitPercent.toFixed(2)}%`, 'exit')
        highGrowthToken.exitPrice = currentPrice
        highGrowthToken.exitTime = Date.now()
        highGrowthToken.percentageGain = exitPercent
        highGrowthToken.finalDecay = (highGrowthToken.peakGrowth - growthRate) / highGrowthToken.peakGrowth
        highGrowthToken.exitReason = 'Growth Decay'

        // Execute exit trade if trading is enabled
        if (tradingEnabled.value && highGrowthToken.entryWallet) {
          executeTrade({
            mint: mint,
            action: 'sell',
            wallet_public_key: highGrowthToken.entryWallet,
            amount: 100,  // Sell 100% of tokens
            denominated_in_sol: false
          }).then(result => {
            addLog(`Exit trade executed for ${token.name}: ${result.signature}`, 'trade')
            highGrowthToken.exitTx = result.signature
          }).catch(error => {
            addLog(`Failed to execute exit trade for ${token.name}: ${error}`, 'error')
          })
        }
      }
    }
  })
}

const executeTrade = async (trade) => {
  try {
    const response = await fetch('http://localhost:8000/execute-trade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(trade)
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to execute trade')
    }
    
    const result = await response.json()
    addLog(
      `${trade.action.toUpperCase()} ${trade.amount} ${trade.denominated_in_sol ? 'SOL' : '%'} of ${trade.mint}`,
      'trade',
      result.signature
    )
    return result
  } catch (error) {
    throw error
  }
}

const toggleTradingMode = () => {
  if (!walletStatus.value.active_wallets) {
    addLog('Cannot enable trading mode: No active wallets', 'error')
    return
  }
  
  tradingEnabled.value = !tradingEnabled.value
  localStorage.setItem('tradingEnabled', tradingEnabled.value.toString())
  
  addLog(`Trading mode ${tradingEnabled.value ? 'enabled' : 'disabled'}`, 'info')
  
  // Update UI to show trading status
  if (tradingEnabled.value) {
    addLog('Trading mode enabled - Will execute trades for new high growth tokens', 'success')
  } else {
    addLog('Trading mode disabled - Position tracking only', 'info')
  }
}

const formatDuration = (startTime, endTime = Date.now()) => {
  const duration = Math.floor((endTime - startTime) / 1000) // duration in seconds
  
  if (duration < 60) return `${duration}s`
  if (duration < 3600) return `${Math.floor(duration / 60)}m ${duration % 60}s`
  const hours = Math.floor(duration / 3600)
  const minutes = Math.floor((duration % 3600) / 60)
  return `${hours}h ${minutes}m`
}

const manualExitPosition = async (token) => {
  if (token.hasStartedTracking && !token.exitPrice) {
    token.exitPrice = token.currentPrice
    token.exitTime = Date.now()
    token.percentageGain = ((token.exitPrice - token.entryPrice) / token.entryPrice) * 100
    token.finalDecay = (token.peakGrowth - token.currentGrowth) / token.peakGrowth
    token.exitReason = 'Manual'
    addLog(`Position Exit: ${token.name} (Manual) ${token.percentageGain.toFixed(2)}%`, 'exit')

    // Execute exit trade if trading is enabled and we have an entry trade
    if (tradingEnabled.value && token.entryWallet) {
      try {
        const result = await executeTrade({
          mint: token.mint,
          action: 'sell',
          wallet_public_key: token.entryWallet,
          amount: 100,  // Sell 100% of tokens
          denominated_in_sol: false
        })
        addLog(`Manual exit trade executed for ${token.name}: ${result.signature}`, 'trade')
        token.exitTx = result.signature
      } catch (error) {
        addLog(`Failed to execute manual exit trade for ${token.name}: ${error}`, 'error')
      }
    }
  }
}

const setTradingMode = async (enabled, test) => {
  try {
    const response = await fetch('http://localhost:8000/trading-mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: enabled,
        test_mode: test
      })
    })
    if (response.ok) {
      tradingEnabled.value = enabled
      testMode.value = test
    } else {
      console.error('Failed to set trading mode:', await response.text())
    }
  } catch (error) {
    console.error('Error setting trading mode:', error)
  }
}

const addWallet = async () => {
  if (isAddingWallet.value) return
  isAddingWallet.value = true
  
  try {
    const response = await fetch('http://localhost:8000/wallet', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'add',
        public_key: newWallet.value.publicKey,
        private_key: newWallet.value.privateKey,
        api_key: newWallet.value.apiKey,
        pool: newWallet.value.pool
      })
    })
    
    if (!response.ok) {
      const error = await response.json()
      addLog(`Failed to add wallet: ${error.detail}`, 'error')
      throw new Error(error.detail || 'Failed to add wallet')
    }
    
    // Clear form
    newWallet.value = { publicKey: '', privateKey: '', apiKey: '', pool: 'pump' }
    // Refresh wallet list
    await fetchWalletStatus()
    addLog('Wallet added successfully', 'success')
  } catch (error) {
    addLog(`Error adding wallet: ${error.message}`, 'error')
    throw error
  } finally {
    isAddingWallet.value = false
  }
}

const removeWallet = async (publicKey) => {
  if (isRemovingWallet.value === publicKey) return
  isRemovingWallet.value = publicKey
  
  try {
    const response = await fetch('http://localhost:8000/wallet', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'remove',
        public_key: publicKey
      })
    })
    
    if (!response.ok) {
      const error = await response.json()
      addLog(`Failed to remove wallet: ${error.detail}`, 'error')
      throw new Error(error.detail || 'Failed to remove wallet')
    }
    
    await fetchWalletStatus()
    addLog('Wallet removed successfully', 'success')
  } catch (error) {
    addLog(`Error removing wallet: ${error.message}`, 'error')
    throw error
  } finally {
    isRemovingWallet.value = null
  }
}

const updateGlobalSettings = async () => {
  try {
    const response = await fetch('http://localhost:8000/trading-settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        slippage: globalSlippage.value,
        priority_fee: globalPriorityFee.value
      })
    })
    
    if (!response.ok) {
      const error = await response.json()
      addLog(`Failed to update settings: ${error.detail}`, 'error')
      throw new Error(error.detail || 'Failed to update settings')
    }
    
    addLog('Trading settings updated successfully', 'success')
  } catch (error) {
    addLog(`Error updating settings: ${error.message}`, 'error')
    throw error
  }
}

const fetchWalletStatus = async () => {
  try {
    const response = await fetch('http://localhost:8000/wallet-status')
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to fetch wallet status')
    }
    
    const data = await response.json()
    walletStatus.value = data
    wallets.value = data.wallets
  } catch (error) {
    addLog(`Error fetching wallet status: ${error.message}`, 'error')
  }
}

const handleTransactionComplete = async () => {
  if (tradingEnabled.value && !testMode.value) {
    await fetchWalletStatus()
  }
}

const emergencyStop = async () => {
  if (!confirm('Are you sure you want to stop all trading and close all positions?')) {
    return
  }
  
  try {
    const response = await fetch('http://localhost:8000/emergency-stop', {
      method: 'POST'
    })
    if (response.ok) {
      const result = await response.json()
      addLog(`Emergency stop executed. Closed ${result.positions_closed} positions.`, 'warning')
    }
  } catch (error) {
    console.error('Error executing emergency stop:', error)
    addLog('Failed to execute emergency stop', 'error')
  }
}

const updateGlobalSlippage = async () => {
  try {
    const response = await fetch('http://localhost:8000/trading-settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slippage: globalSlippage.value })
    })
    if (!response.ok) {
      console.error('Failed to update global slippage')
    }
  } catch (error) {
    console.error('Error updating global slippage:', error)
  }
}

const toggleDebugConsole = () => {
  isDebugExpanded.value = !isDebugExpanded.value
}

const clearLogs = () => {
  logs.value = []
}

const filteredLogs = computed(() => {
  return logs.value.filter(log => {
    if (log.type === 'trade' && !debugFilters.value.trades) return false
    if (log.type === 'error' && !debugFilters.value.errors) return false
    if (log.type === 'wallet' && !debugFilters.value.wallet) return false
    if (log.type === 'exit' && !debugFilters.value.exits) return false
    if (log.type === 'success' && !debugFilters.value.wallet) return false
    return true
  })
})

onMounted(() => {
  const init = async () => {
  addLog('Application started')
  await fetchSolPrice()
    await fetchWalletStatus()  // Initial wallet status fetch
    
    // Check if trading mode should be enabled
    if (tradingEnabled.value && walletStatus.value.active_wallets === 0) {
      tradingEnabled.value = false
      localStorage.setItem('tradingEnabled', 'false')
      addLog('Trading mode disabled: No active wallets', 'warning')
    } else if (tradingEnabled.value) {
      addLog('Trading mode enabled - Will execute trades for new high growth tokens', 'success')
    }
    
    priceInterval = setInterval(fetchSolPrice, 300000)  // Update SOL price every 5 minutes
  timeInterval = setInterval(() => forceUpdate.value++, 100)
  cullInterval = setInterval(cullDeadTokens, 1000)
  growthCheckInterval = setInterval(checkHighGrowthTokens, 100)
    walletStatusInterval = setInterval(fetchWalletStatus, 10000)  // Poll wallet status every 10 seconds
  connectWebSocket()
  }
  init()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
  if (priceInterval) {
    clearInterval(priceInterval)
  }
  if (timeInterval) {
    clearInterval(timeInterval)
  }
  if (cullInterval) {
    clearInterval(cullInterval)
  }
  if (growthCheckInterval) {
    clearInterval(growthCheckInterval)
  }
  if (walletStatusInterval) {
    clearInterval(walletStatusInterval)
  }
})

// Add computed property for filtered high growth tokens
const sortedHighGrowthTokens = computed(() => {
  return Object.values(highGrowthTokens.value)
    .sort((a, b) => {
      // First, put waiting tokens at the top
      if (!a.hasStartedTracking && b.hasStartedTracking) return -1
      if (a.hasStartedTracking && !b.hasStartedTracking) return 1
      
      // If both are waiting, sort by remaining time
      if (!a.hasStartedTracking && !b.hasStartedTracking) {
        return (b.potentialEntryTime || 0) - (a.potentialEntryTime || 0)
      }
      
      // Then separate active and exited tokens
      if (!a.exitPrice && b.exitPrice) return -1  // a is active, b is exited -> a comes first
      if (a.exitPrice && !b.exitPrice) return 1   // a is exited, b is active -> b comes first
      
      // If both are active, sort by current growth rate
      if (!a.exitPrice && !b.exitPrice) {
        return b.currentGrowth - a.currentGrowth
      }
      
      // If both are exited, sort by percentage gain
      return b.percentageGain - a.percentageGain
    })
})

// Add this before the other computed properties
const trackingCriteriaDescription = computed(() => {
  return `High Growth Tracking Criteria:
• Entry: Growth rate ≥ 20 for 3 seconds
• Must maintain price during waiting period
• Growth can't drop >50% during waiting period
• Cancel if growth rate >200 in first 5s
• Exit: Growth drops below ${(0.50 * 100).toFixed(0)}% of average growth
• Exit requires >30 samples (${(30 * 100).toFixed(0)}ms each)
• Stop Loss: -50% from entry price`
})

// Add before the trackingCriteriaDescription computed property
const netPercentageGain = computed(() => {
  return Object.values(highGrowthTokens.value).reduce((total, token) => {
    if (token.hasStartedTracking) {
      if (token.exitPrice) {
        // Use the final percentage gain for completed positions
        return total + token.percentageGain
      } else {
        // Calculate current gain/loss for active positions
        const currentGain = ((token.currentPrice - token.entryPrice) / token.entryPrice) * 100
        return total + currentGain
      }
    }
    return total
  }, 0)
})

const getTradeStatus = (token) => {
  switch (token.trade_status) {
    case 'pending_buy':
      return 'Buying...'
    case 'bought':
      return 'Active'
    case 'pending_sell':
      return 'Selling...'
    case 'sold':
      return 'Sold'
    default:
      return 'Active'
  }
}

const calculateTradeAmount = (walletBalance, slippage, priorityFee) => {
  // Convert slippage to decimal
  const slippageDecimal = slippage / 100
  
  // Reserve amount for priority fee
  const availableAfterFee = walletBalance - priorityFee
  
  // Calculate maximum trade amount considering slippage
  // Formula: max_trade = available / (1 + slippage)
  const maxTrade = availableAfterFee / (1 + slippageDecimal)
  
  // Cap at 0.5 SOL
  return Math.min(maxTrade, 0.5)
}

const getNextAvailableWallet = () => {
  // Get all active wallets with sufficient balance and no errors
  const availableWallets = walletStatus.value.wallets.filter(w => 
    w.is_active && w.error_count < 3 && w.balance >= 0.1
  )
  
  if (availableWallets.length === 0) {
    return null
  }
  
  // Sort by last used time (undefined = never used)
  availableWallets.sort((a, b) => {
    if (!a.last_used && !b.last_used) return 0
    if (!a.last_used) return -1
    if (!b.last_used) return 1
    return a.last_used - b.last_used
  })
  
  // Return the least recently used wallet
  return availableWallets[0]
}

const manualEntryTrade = async (token) => {
  if (!tradingEnabled.value || walletStatus.value.active_wallets === 0) return
  
  try {
    // Find least recently used wallet
    const wallet = wallets.value.reduce((prev, curr) => {
      if (!prev.last_used) return curr
      if (!curr.last_used) return prev
      return new Date(prev.last_used) < new Date(curr.last_used) ? prev : curr
    })

    // Calculate position size (0.1 SOL worth of tokens)
    const positionSizeInSol = 0.1
    
    // Execute buy trade
    const result = await executeTrade({
      mint: token.mint,
      action: 'buy',
      wallet_public_key: wallet.public_key,
      amount: positionSizeInSol,
      denominated_in_sol: true
    })
    
    addLog(`Manual entry trade executed for ${token.name}: ${result.signature}`, 'trade')
    token.entryTx = result.signature
    token.entryWallet = wallet.public_key
  } catch (error) {
    addLog(`Failed to execute manual entry trade for ${token.name}: ${error}`, 'error')
  }
}
</script>

<style>
html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  background: #0f172a;
  overflow: hidden;
}

.container {
  width: 100%;
  height: 100vh;
  padding: 1.5rem;
  background: #0f172a;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
}

.main-content {
  width: 100%;
  max-width: 1800px;
  margin: 0 auto;
  display: flex;
  gap: 1.5rem;
  justify-content: center;
  align-items: flex-start;
}

.content-wrapper {
  width: 960px;  /* Fixed width for main content */
  flex: 0 0 auto;  /* Prevent flexbox from growing/shrinking */
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.header {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #2a2f3e;
  box-sizing: border-box;
  background: #1a1f2e;
}

.status-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.connection-status {
  padding: 0.25rem 1rem;
  border-radius: 1rem;
  background-color: #991b1b;
  color: white;
  font-size: 0.9rem;
  border: 1px solid #ef4444;
}

.connection-status.connected {
  background-color: #166534;
  border-color: #22c55e;
}

.token-count {
  padding: 0.25rem 1rem;
  border-radius: 1rem;
  background: #334155;
  color: #94a3b8;
  font-size: 0.9rem;
  border: 1px solid #475569;
}

.reset-button {
  padding: 0.25rem 1rem;
  border-radius: 1rem;
  background: #450a0a;
  color: #fecaca;
  border: 1px solid #dc2626;
  cursor: pointer;
  font-size: 0.9rem;
}

.reset-button:hover {
  background: #991b1b;
}

.token-container {
  background: #1a1f2e;
  border: 1px solid #2a2f3e;
  border-radius: 0.5rem;
  padding: 1rem;
  height: 645px;  /* Reduced height for 2 rows of tokens */
}

.token-list {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  box-sizing: border-box;
}

.token-card {
  background: #0f172a;
  border-radius: 0.5rem;
  padding: 0.75rem;
  border: 1px solid #2a2f3e;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 0;
}

.token-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 0.375rem;
  border-bottom: 1px solid #2a2f3e;
  gap: 0.375rem;
  min-width: 0;
}

.token-title {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  min-width: 0;
  flex: 1;
  overflow: hidden;
}

.token-symbol {
  padding: 0.125rem 0.25rem;
  background: #1a1f2e;
  border-radius: 0.25rem;
  color: #94a3b8;
  font-size: 0.75rem;
  border: 1px solid #2a2f3e;
}

.token-time {
  color: #94a3b8;
  font-size: 0.8rem;
  white-space: nowrap;
  flex-shrink: 0;
}

.metrics-row {
  display: flex;
  gap: 0.75rem;
  width: 100%;
}

.metrics-row .growth-rate-section,
.metrics-row .market-cap {
  flex: 1;
  min-width: 0;
}

.growth-rate-section {
  padding: 0.75rem;
  background: #1a1f2e;
  border-radius: 0.5rem;
  text-align: center;
  border: 1px solid #2a2f3e;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.market-cap {
  padding: 0.75rem;
  background: #1a1f2e;
  border-radius: 0.5rem;
  text-align: center;
  border: 1px solid #2a2f3e;
}

.growth-value {
  color: #e2e8f0;
  font-weight: 600;
  font-size: 1.25rem;
  position: relative;
  z-index: 1;
}

.metric-label {
  color: #94a3b8;
  font-size: 0.75rem;
  margin-bottom: 0.25rem;
}

.token-metrics {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.metric {
  padding: 0.75rem;
  background: #1a1f2e;
  border-radius: 0.5rem;
  text-align: center;
  border: 1px solid #2a2f3e;
  min-width: 0;
  overflow: hidden;
}

.metric-value {
  color: #e2e8f0;
  font-weight: 500;
  font-size: 1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.usd-value {
  color: #22c55e;
  font-size: 0.875rem;
  margin-top: 0.125rem;
}

.token-links {
  padding: 0.375rem;
  background: #1a1f2e;
  border-radius: 0.375rem;
  border: 1px solid #2a2f3e;
}

.link-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
}

.link-label {
  color: #94a3b8;
  white-space: nowrap;
}

.address-link {
  color: #60a5fa;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.address-link:hover {
  color: #93c5fd;
  text-decoration: underline;
}

.external-link {
  font-size: 0.8em;
  opacity: 0.7;
}

h1 {
  margin: 0;
  font-size: 1.5rem;
  background: linear-gradient(135deg, #60a5fa, #22c55e);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

h3 {
  margin: 0;
  font-size: 1rem;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

h3 a {
  color: #e2e8f0;
  text-decoration: none;
}

h3 a:hover {
  color: #60a5fa;
}

.warning {
  color: #ef4444;  /* red-500 */
  font-size: 0.8rem;
  font-weight: 500;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.high-growth-sidebar {
  width: 320px;
  background: #1a1f2e;
  border: 1px solid #2a2f3e;
  border-radius: 0.5rem;
  display: flex;
  flex-direction: column;
  height: 764px;  /* Match token container height */
}

.sidebar-header {
  padding: 1rem;
  border-bottom: 1px solid #2a2f3e;
}

.sidebar-header h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  color: #e2e8f0;
}

.sidebar-subtitle {
  color: #94a3b8;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.high-growth-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.high-growth-card {
  background: #0f172a;
  border: 1px solid #2a2f3e;
  border-radius: 0.375rem;
  padding: 0.75rem;
  transition: all 0.3s ease;
}

.high-growth-card.waiting {
  border-color: #60a5fa;
  box-shadow: 0 0 15px rgba(96, 165, 250, 0.15);
  background: linear-gradient(to bottom, #0f172a, rgba(96, 165, 250, 0.05));
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { border-color: #60a5fa; }
  50% { border-color: #93c5fd; }
  100% { border-color: #60a5fa; }
}

.high-growth-card.positive-glow {
  border-color: #22c55e;
  box-shadow: 0 0 15px rgba(34, 197, 94, 0.15);
  background: linear-gradient(to bottom, #0f172a, rgba(34, 197, 94, 0.05));
}

.high-growth-card.negative-glow {
  border-color: #ef4444;
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.15);
  background: linear-gradient(to bottom, #0f172a, rgba(239, 68, 68, 0.05));
}

.high-growth-card.exited-positive {
  border-color: #22c55e;
  background: linear-gradient(to bottom, #0f172a, rgba(34, 197, 94, 0.02));
}

.high-growth-card.exited-negative {
  border-color: #ef4444;
  background: linear-gradient(to bottom, #0f172a, rgba(239, 68, 68, 0.02));
}

.positive-value {
  color: #22c55e !important;
}

.negative-value {
  color: #ef4444 !important;
}

.high-growth-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.high-growth-title h3 {
  margin: 0;
  font-size: 0.875rem;
}

.growth-stats {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.growth-badge {
  background: #1e293b;
  color: #94a3b8;
  padding: 0.25rem 0.5rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid #2a2f3e;
}

.growth-badge.positive-badge {
  background: #166534;
  color: #22c55e;
  border-color: #22c55e;
}

.growth-badge.negative-badge {
  background: #991b1b;
  color: #ef4444;
  border-color: #ef4444;
}

.price-metrics {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.price-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
}

.price-label {
  color: #94a3b8;
}

.price-value {
  color: #e2e8f0;
  font-family: monospace;
}

.total-gain {
  text-align: right;
  font-weight: 600;
  font-size: 0.875rem;
  color: #ef4444;
  margin-top: 0.375rem;
  padding-top: 0.375rem;
  border-top: 1px solid #2a2f3e;
}

.total-gain.positive {
  color: #22c55e;
}

.countdown-badge {
  background: #1e293b;
  color: #60a5fa;
  padding: 0.25rem 0.5rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid #60a5fa;
  animation: pulse 2s infinite;
}

.live-gain {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.375rem;
  padding-top: 0.375rem;
  border-top: 1px solid #2a2f3e;
  font-weight: 600;
  font-size: 0.875rem;
}

.live-gain .positive {
  color: #22c55e;
}

.live-gain .negative {
  color: #ef4444;
}

.active-chip {
  background: #166534;
  color: #22c55e;
  padding: 0.125rem 0.5rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  border: 1px solid #22c55e;
  animation: glow 2s infinite;
}

@keyframes glow {
  0% { box-shadow: 0 0 5px rgba(34, 197, 94, 0.2); }
  50% { box-shadow: 0 0 10px rgba(34, 197, 94, 0.4); }
  100% { box-shadow: 0 0 5px rgba(34, 197, 94, 0.2); }
}

.title-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.info-tooltip {
  position: relative;
  display: inline-block;
}

.info-icon {
  color: #60a5fa;
  cursor: help;
  font-size: 1rem;
  opacity: 0.8;
  transition: opacity 0.2s;
  background: #1e293b;
  padding: 0.25rem 0.5rem;
  border-radius: 1rem;
  border: 1px solid #2a2f3e;
}

.info-icon:hover {
  opacity: 1;
}

.tooltip-content {
  visibility: hidden;
  position: absolute;
  left: 100%;
  top: 50%;
  transform: translateY(-50%);
  margin-left: 0.75rem;
  padding: 0.75rem;
  background: #1e293b;
  border: 1px solid #2a2f3e;
  border-radius: 0.5rem;
  color: #e2e8f0;
  font-size: 0.875rem;
  white-space: pre-line;
  width: max-content;
  max-width: 350px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  z-index: 10;
}

.info-tooltip:hover .tooltip-content {
  visibility: visible;
}

.tooltip-content::before {
  content: "";
  position: absolute;
  right: 100%;
  top: 50%;
  transform: translateY(-50%);
  border-width: 6px;
  border-style: solid;
  border-color: transparent #2a2f3e transparent transparent;
}

.time-badge {
  background: #1e293b;
  color: #94a3b8;
  padding: 0.25rem 0.5rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 500;
  border: 1px solid #2a2f3e;
}

.net-percentage {
  font-size: 0.875rem;
  font-weight: 600;
}

.net-percentage.positive {
  color: #22c55e;
}

.net-percentage.negative {
  color: #ef4444;
}

.position-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.close-button {
  background: #991b1b;
  color: #ef4444;
  padding: 0.125rem 0.5rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  border: 1px solid #ef4444;
  cursor: pointer;
  transition: all 0.2s ease;
  animation: glow-red 2s infinite;
}

@keyframes glow-red {
  0% { box-shadow: 0 0 5px rgba(239, 68, 68, 0.2); }
  50% { box-shadow: 0 0 10px rgba(239, 68, 68, 0.4); }
  100% { box-shadow: 0 0 5px rgba(239, 68, 68, 0.2); }
}

.close-button:hover {
  background: #7f1d1d;
}

.status-chips {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.trading-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.mode-toggle {
  display: flex;
  gap: 0.25rem;
  background: #1a1f2e;
  padding: 0.25rem;
  border-radius: 1rem;
  border: 1px solid #2a2f3e;
}

.mode-button {
  padding: 0.25rem 0.75rem;
  border-radius: 0.75rem;
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s ease;
}

.mode-button.active {
  background: #0f172a;
  color: #e2e8f0;
}

.wallet-status {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 0.75rem;
  background: #1a1f2e;
  border: 1px solid #2a2f3e;
  border-radius: 1rem;
  color: #e2e8f0;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.wallet-status:hover {
  border-color: #60a5fa;
}

.total-value {
  padding-left: 1rem;
  border-left: 1px solid #2a2f3e;
  color: #22c55e;
  font-weight: 500;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1a1f2e;
  border: 1px solid #2a2f3e;
  border-radius: 0.5rem;
  padding: 1.5rem;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.modal-header h2 {
  margin: 0;
  color: #e2e8f0;
}

.close-modal {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
}

.close-modal:hover {
  color: #e2e8f0;
}

.wallet-form {
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #2a2f3e;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  color: #94a3b8;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}

.form-group input {
  width: 100%;
  padding: 0.5rem;
  background: #0f172a;
  border: 1px solid #2a2f3e;
  border-radius: 0.375rem;
  color: #e2e8f0;
  font-size: 0.875rem;
}

.form-group input:focus {
  outline: none;
  border-color: #60a5fa;
}

.add-wallet-button {
  width: 100%;
  padding: 0.75rem;
  background: #1d4ed8;
  color: white;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.add-wallet-button:hover {
  background: #2563eb;
}

.wallet-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.wallet-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #0f172a;
  border: 1px solid #2a2f3e;
  border-radius: 0.375rem;
}

.wallet-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.wallet-address {
  color: #e2e8f0;
  font-size: 0.875rem;
  font-family: monospace;
}

.wallet-balance {
  color: #94a3b8;
  font-size: 0.75rem;
}

.remove-wallet {
  padding: 0.375rem 0.75rem;
  background: #991b1b;
  color: #fecaca;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.75rem;
  transition: all 0.2s ease;
}

.remove-wallet:hover {
  background: #7f1d1d;
}

.trade-status {
  margin-left: auto;
  font-size: 0.75rem;
}

.tx-link {
  color: #60a5fa;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.375rem;
  background: #1e293b;
  border-radius: 1rem;
  border: 1px solid #2a2f3e;
  transition: all 0.2s ease;
}

.tx-link:hover {
  color: #93c5fd;
  border-color: #60a5fa;
}

.price-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.add-wallet-button:disabled,
.remove-wallet:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.input-help {
  color: #94a3b8;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.form-group select {
  width: 100%;
  padding: 0.5rem;
  background: #0f172a;
  border: 1px solid #2a2f3e;
  border-radius: 0.375rem;
  color: #e2e8f0;
  font-size: 0.875rem;
}

.form-group select:focus {
  outline: none;
  border-color: #60a5fa;
}

.emergency-stop-button {
  padding: 0.25rem 1rem;
  border-radius: 1rem;
  background: #7f1d1d;
  color: #fecaca;
  border: 1px solid #dc2626;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  animation: pulse-red 2s infinite;
}

.emergency-stop-button:hover {
  background: #991b1b;
}

@keyframes pulse-red {
  0% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(220, 38, 38, 0); }
  100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
}

.active-chip.pending {
  animation: pulse-yellow 2s infinite;
  background: #854d0e;
  color: #fef08a;
  border-color: #facc15;
}

@keyframes pulse-yellow {
  0% { box-shadow: 0 0 0 0 rgba(250, 204, 21, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(250, 204, 21, 0); }
  100% { box-shadow: 0 0 0 0 rgba(250, 204, 21, 0); }
}

.pending-trade {
  border-color: #facc15 !important;
  box-shadow: 0 0 15px rgba(250, 204, 21, 0.15) !important;
  background: linear-gradient(to bottom, #0f172a, rgba(250, 204, 21, 0.05)) !important;
}

.global-settings {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: #1e293b;
  border-radius: 0.5rem;
  border: 1px solid #2a2f3e;
}

.global-settings .form-group {
  margin-bottom: 0;
}

.global-settings label {
  color: #e2e8f0;
  font-weight: 500;
}

/* Debug Console Styles */
.debug-console {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #1a1f2e;
  border-top: 1px solid #2a2f3e;
  z-index: 1000;
  max-height: 30vh;
  display: flex;
  flex-direction: column;
}

.debug-header {
  padding: 0.5rem 1rem;
  background: #0f172a;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #2a2f3e;
}

.debug-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.debug-filters {
  padding: 0.5rem;
  display: flex;
  gap: 1rem;
  border-bottom: 1px solid #2a2f3e;
}

.debug-filters label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #94a3b8;
}

.clear-logs {
  margin-left: auto;
  padding: 0.25rem 0.75rem;
  background: #991b1b;
  color: #fecaca;
  border: 1px solid #dc2626;
  border-radius: 0.25rem;
  cursor: pointer;
}

.log-container {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
  font-family: monospace;
  font-size: 0.875rem;
}

.log-entry {
  padding: 0.25rem 0;
  display: flex;
  gap: 0.5rem;
}

.log-time {
  color: #94a3b8;
  flex-shrink: 0;
}

.log-entry.trade {
  color: #22c55e;
}

.log-entry.error {
  color: #ef4444;
}

.log-entry.wallet {
  color: #60a5fa;
}

/* Transaction Info Styles */
.trade-status-info {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #1e293b;
  border-radius: 0.375rem;
  border: 1px solid #2a2f3e;
}

.status-message {
  color: #facc15;
  font-size: 0.875rem;
  font-weight: 500;
}

.error-message {
  color: #ef4444;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.transaction-info {
  margin-top: 0.5rem;
  font-size: 0.75rem;
}

.transaction-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.25rem;
}

.transaction-type {
  color: #94a3b8;
}

.transaction-link {
  color: #60a5fa;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.transaction-link:hover {
  text-decoration: underline;
}

@media (max-width: 1000px) {
  .container {
    height: auto;
    min-height: 100vh;
  }

  .main-content {
    flex-direction: column;
    align-items: center;
  }
  
  .content-wrapper {
    width: 100%;
    max-width: 960px;
  }
  
  .high-growth-sidebar {
    width: 100%;
    max-width: 960px;
    height: 400px;
  }
  
  .token-container {
    height: auto;
    min-height: 400px;
  }
}

.wallet-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.last-used {
  color: #94a3b8;
  font-size: 0.75rem;
}

.pool-info {
  color: #94a3b8;
  font-size: 0.75rem;
  padding: 0.125rem 0.375rem;
  background: #1e293b;
  border-radius: 1rem;
  border: 1px solid #2a2f3e;
  display: inline-block;
}

.wallet-summary {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.wallet-count {
  font-weight: 500;
}

.wallet-cycle {
  font-size: 0.75rem;
  color: #94a3b8;
}

.trade-links {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.trade-link {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.trade-wallet {
  font-size: 0.75rem;
  color: #94a3b8;
  padding-left: 0.5rem;
}

.wallet-tag {
  font-size: 0.75rem;
  color: #94a3b8;
  padding: 0.125rem 0.375rem;
  background: #1e293b;
  border-radius: 1rem;
  border: 1px solid #2a2f3e;
  margin-left: 0.375rem;
}

.transaction-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  padding: 0.25rem 0;
}

.transaction-type {
  color: #94a3b8;
  display: flex;
  align-items: center;
}

.transaction-link {
  color: #60a5fa;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.375rem;
  background: #1e293b;
  border-radius: 1rem;
  border: 1px solid #2a2f3e;
  transition: all 0.2s ease;
}

.transaction-link:hover {
  border-color: #60a5fa;
  text-decoration: none;
}

/* Trading Mode Button Styles */
.trading-mode-button {
  padding: 0.375rem 1rem;
  border-radius: 1rem;
  font-size: 0.875rem;
  background: #1e293b;
  color: #94a3b8;
  border: 1px solid #2a2f3e;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.trading-mode-button:hover {
  border-color: #60a5fa;
}

.trading-mode-button.active {
  background: #166534;
  color: #22c55e;
  border-color: #22c55e;
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.2);
}

.trading-mode-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Wallet Management Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: #1a1f2e;
  border: 1px solid #2a2f3e;
  border-radius: 0.75rem;
  padding: 1.5rem;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.wallet-settings {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: #0f172a;
  border: 1px solid #2a2f3e;
  border-radius: 0.5rem;
}

.settings-row {
  display: flex;
  gap: 1rem;
  margin-top: 0.75rem;
}

.settings-row label {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  color: #94a3b8;
  font-size: 0.875rem;
}

.settings-row input {
  padding: 0.5rem;
  border-radius: 0.375rem;
  background: #1e293b;
  border: 1px solid #2a2f3e;
  color: #e2e8f0;
  width: 120px;
  transition: all 0.2s;
}

.settings-row input:focus {
  border-color: #60a5fa;
  outline: none;
}

.wallet-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.wallet-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #0f172a;
  border: 1px solid #2a2f3e;
  border-radius: 0.5rem;
  transition: all 0.2s;
}

.wallet-item:hover {
  border-color: #60a5fa;
}

.wallet-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.wallet-address {
  color: #e2e8f0;
  font-family: monospace;
  font-size: 0.875rem;
}

.wallet-balance {
  color: #22c55e;
  font-size: 0.875rem;
  font-weight: 500;
}

.remove-wallet {
  padding: 0.375rem 0.75rem;
  border-radius: 0.5rem;
  background: #991b1b;
  color: #fecaca;
  border: 1px solid #dc2626;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.remove-wallet:hover:not(:disabled) {
  background: #7f1d1d;
}

.remove-wallet:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.add-wallet-form {
  padding: 1rem;
  background: #0f172a;
  border: 1px solid #2a2f3e;
  border-radius: 0.5rem;
}

.form-row {
  margin-bottom: 0.75rem;
}

.form-row input,
.form-row select {
  width: 100%;
  padding: 0.5rem;
  border-radius: 0.375rem;
  background: #1e293b;
  border: 1px solid #2a2f3e;
  color: #e2e8f0;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.form-row input:focus,
.form-row select:focus {
  border-color: #60a5fa;
  outline: none;
}

.add-wallet-button {
  width: 100%;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background: #1d4ed8;
  color: white;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s;
}

.add-wallet-button:hover:not(:disabled) {
  background: #2563eb;
}

.add-wallet-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.trade-button {
  padding: 0.375rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  background: #1d4ed8;
  color: white;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.trade-button:hover:not(:disabled) {
  background: #2563eb;
}

.trade-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-spinner {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.trading-badge {
  padding: 0.25rem 0.5rem;
  background: #166534;
  color: #22c55e;
  border: 1px solid #22c55e;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.trading-badge::before {
  content: '';
  width: 0.5rem;
  height: 0.5rem;
  background: #22c55e;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.high-growth-card.trading-enabled {
  border-color: #22c55e;
  box-shadow: 0 0 15px rgba(34, 197, 94, 0.15);
}

.log-entry.exit {
  color: #eab308;
  font-weight: 500;
}
</style>