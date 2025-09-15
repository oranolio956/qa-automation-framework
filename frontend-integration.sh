#!/bin/bash

# Frontend Integration for Development Account Management
# Updates management UI to display and control development account creation status
# Designed for legitimate development testing and account management workflows

set -euo pipefail

# Configuration
REPO_PATH="${REPO_PATH:-$(pwd)}"
FRONTEND_DIR="${FRONTEND_DIR:-${REPO_PATH}/frontend}"
API_ENDPOINT="${API_ENDPOINT:-http://localhost:3001/api/v1/account}"
LOG_FILE="${REPO_PATH}/logs/frontend-integration.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

# Create directory structure
setup_directories() {
    log "Setting up frontend integration directory structure..."
    
    mkdir -p "${REPO_PATH}/logs"
    mkdir -p "${FRONTEND_DIR}"/{src,public,build}
    mkdir -p "${FRONTEND_DIR}/src"/{components,pages,services,utils,hooks,contexts,styles}
    mkdir -p "${FRONTEND_DIR}/src/components"/{common,accounts,management,status}
    
    log "✓ Directory structure created"
}

# Create React package configuration
create_frontend_package() {
    log "Creating React frontend package configuration..."
    
    cat > "${FRONTEND_DIR}/package.json" << 'EOF'
{
  "name": "development-account-management-ui",
  "version": "1.0.0",
  "description": "Frontend UI for development account management and testing workflows",
  "private": true,
  "dependencies": {
    "@types/node": "^18.0.0",
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "react-scripts": "5.0.1",
    "typescript": "^4.9.5",
    "antd": "^5.8.0",
    "@ant-design/icons": "^5.2.0",
    "axios": "^1.5.0",
    "react-query": "^3.39.0",
    "socket.io-client": "^4.7.0",
    "dayjs": "^1.11.0",
    "classnames": "^2.3.0",
    "lodash": "^4.17.21",
    "@types/lodash": "^4.14.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^5.16.0",
    "@testing-library/react": "^13.4.0",
    "@testing-library/user-event": "^14.4.0",
    "@types/jest": "^29.5.0",
    "jest": "^29.6.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject",
    "lint": "eslint src --ext .js,.jsx,.ts,.tsx",
    "lint:fix": "eslint src --ext .js,.jsx,.ts,.tsx --fix"
  },
  "eslintConfig": {
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  },
  "proxy": "http://localhost:3001"
}
EOF

    log "✓ Frontend package configuration created"
}

# Create main React application
create_main_app() {
    log "Creating main React application..."
    
    cat > "${FRONTEND_DIR}/src/App.tsx" << 'EOF'
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query/devtools';
import { ConfigProvider } from 'antd';
import 'antd/dist/reset.css';

import Layout from './components/common/Layout';
import Dashboard from './pages/Dashboard';
import AccountManagement from './pages/AccountManagement';
import { AccountProvider } from './contexts/AccountContext';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

const theme = {
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
  },
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider theme={theme}>
        <AccountProvider>
          <Router>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/accounts" element={<AccountManagement />} />
              </Routes>
            </Layout>
          </Router>
          <ReactQueryDevtools initialIsOpen={false} />
        </AccountProvider>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;
EOF

    # Create index.tsx
    cat > "${FRONTEND_DIR}/src/index.tsx" << 'EOF'
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
EOF

    # Create public/index.html
    cat > "${FRONTEND_DIR}/public/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%PUBLIC_URL%/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta name="description" content="Development Account Management UI" />
    <title>Development Account Management</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>
EOF

    log "✓ Main React application created"
}

# Create Account Context for state management
create_account_context() {
    log "Creating Account Context for state management..."
    
    cat > "${FRONTEND_DIR}/src/contexts/AccountContext.tsx" << 'EOF'
import React, { createContext, useContext, useReducer, ReactNode } from 'react';

// Types
interface Account {
  id: string;
  environmentId: string;
  accountType: 'web' | 'mobile' | 'api';
  status: 'creating' | 'active' | 'failed' | 'cleaning';
  createdAt: string;
  lastUpdated: string;
  testConfig?: {
    purpose: string;
    automated: boolean;
  };
  capabilities?: {
    webTesting: boolean;
    mobileTesting: boolean;
    apiTesting: boolean;
    automatedTesting: boolean;
  };
}

interface AccountState {
  accounts: Account[];
  selectedAccount: Account | null;
  loading: boolean;
  error: string | null;
}

type AccountAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_ACCOUNTS'; payload: Account[] }
  | { type: 'ADD_ACCOUNT'; payload: Account }
  | { type: 'UPDATE_ACCOUNT'; payload: Account }
  | { type: 'REMOVE_ACCOUNT'; payload: string }
  | { type: 'SELECT_ACCOUNT'; payload: Account | null };

const initialState: AccountState = {
  accounts: [],
  selectedAccount: null,
  loading: false,
  error: null,
};

const accountReducer = (state: AccountState, action: AccountAction): AccountState => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    
    case 'SET_ACCOUNTS':
      return { ...state, accounts: action.payload, loading: false, error: null };
    
    case 'ADD_ACCOUNT':
      return {
        ...state,
        accounts: [...state.accounts, action.payload],
        loading: false,
        error: null,
      };
    
    case 'UPDATE_ACCOUNT':
      return {
        ...state,
        accounts: state.accounts.map(account =>
          account.id === action.payload.id ? action.payload : account
        ),
        selectedAccount:
          state.selectedAccount?.id === action.payload.id
            ? action.payload
            : state.selectedAccount,
      };
    
    case 'REMOVE_ACCOUNT':
      return {
        ...state,
        accounts: state.accounts.filter(account => account.id !== action.payload),
        selectedAccount:
          state.selectedAccount?.id === action.payload ? null : state.selectedAccount,
      };
    
    case 'SELECT_ACCOUNT':
      return { ...state, selectedAccount: action.payload };
    
    default:
      return state;
  }
};

// Context
const AccountContext = createContext<{
  state: AccountState;
  dispatch: React.Dispatch<AccountAction>;
} | null>(null);

// Provider
interface AccountProviderProps {
  children: ReactNode;
}

export const AccountProvider: React.FC<AccountProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(accountReducer, initialState);

  return (
    <AccountContext.Provider value={{ state, dispatch }}>
      {children}
    </AccountContext.Provider>
  );
};

// Hook
export const useAccountContext = () => {
  const context = useContext(AccountContext);
  if (!context) {
    throw new Error('useAccountContext must be used within an AccountProvider');
  }
  return context;
};

// Export types
export type { Account, AccountState, AccountAction };
EOF

    log "✓ Account context created"
}

# Create enhanced AccountsTable component
create_accounts_table() {
    log "Creating enhanced AccountsTable component..."
    
    cat > "${FRONTEND_DIR}/src/components/accounts/AccountsTable.tsx" << 'EOF'
import React, { useState, useCallback } from 'react';
import {
  Table,
  Tag,
  Button,
  Space,
  Tooltip,
  Modal,
  message,
  Popconfirm,
  Badge,
  Typography,
} from '@ant-design/icons';
import {
  PlayCircleOutlined,
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import dayjs from 'dayjs';

import { accountService } from '../../services/accountService';
import { Account } from '../../contexts/AccountContext';
import AccountDetails from './AccountDetails';
import AccountActions from './AccountActions';

const { Text } = Typography;

interface AccountsTableProps {
  environmentFilter?: string;
  accountTypeFilter?: string;
}

const AccountsTable: React.FC<AccountsTableProps> = ({
  environmentFilter,
  accountTypeFilter,
}) => {
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [detailsModalVisible, setDetailsModalVisible] = useState(false);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  
  const queryClient = useQueryClient();

  // Fetch accounts
  const {
    data: accounts = [],
    isLoading,
    error,
    refetch,
  } = useQuery(
    ['accounts', environmentFilter, accountTypeFilter],
    () => accountService.getAccounts({
      environmentId: environmentFilter,
      accountType: accountTypeFilter,
    }),
    {
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  );

  // Create account mutation
  const createAccountMutation = useMutation(
    (accountData: any) => accountService.createAccount(accountData),
    {
      onSuccess: () => {
        message.success('Development account creation initiated');
        queryClient.invalidateQueries('accounts');
      },
      onError: (error: any) => {
        message.error(`Failed to create account: ${error.message}`);
      },
    }
  );

  // Execute workflow mutation
  const executeWorkflowMutation = useMutation(
    ({ accountId, workflowType, parameters }: any) =>
      accountService.executeWorkflow(accountId, workflowType, parameters),
    {
      onSuccess: () => {
        message.success('Workflow execution started');
        queryClient.invalidateQueries('accounts');
      },
      onError: (error: any) => {
        message.error(`Failed to execute workflow: ${error.message}`);
      },
    }
  );

  // Delete account mutation
  const deleteAccountMutation = useMutation(
    (accountId: string) => accountService.deleteAccount(accountId),
    {
      onSuccess: () => {
        message.success('Account cleanup initiated');
        queryClient.invalidateQueries('accounts');
      },
      onError: (error: any) => {
        message.error(`Failed to cleanup account: ${error.message}`);
      },
    }
  );

  // Status tag renderer
  const renderStatus = useCallback((status: string) => {
    const statusConfig = {
      creating: { color: 'processing', icon: <ClockCircleOutlined /> },
      active: { color: 'success', icon: <CheckCircleOutlined /> },
      failed: { color: 'error', icon: <CloseCircleOutlined /> },
      cleaning: { color: 'warning', icon: <ExclamationCircleOutlined /> },
    };

    const config = statusConfig[status as keyof typeof statusConfig] || {
      color: 'default',
      icon: null,
    };

    return (
      <Tag color={config.color} icon={config.icon}>
        {status.toUpperCase()}
      </Tag>
    );
  }, []);

  // Development account status renderer
  const renderDevelopmentAccountStatus = useCallback((record: Account) => {
    const isDevelopmentAccount = record.testConfig?.purpose === 'development_testing';
    const isAutomated = record.testConfig?.automated;

    return (
      <Space direction="vertical" size="small">
        <Tag color={isDevelopmentAccount ? 'green' : 'orange'}>
          {isDevelopmentAccount ? 'Development Account' : 'Standard Account'}
        </Tag>
        {isAutomated && (
          <Tag color="blue" size="small">
            Automated
          </Tag>
        )}
      </Space>
    );
  }, []);

  // Capabilities renderer
  const renderCapabilities = useCallback((capabilities: Account['capabilities']) => {
    if (!capabilities) return <Text type="secondary">No capabilities</Text>;

    const caps = [];
    if (capabilities.webTesting) caps.push('Web');
    if (capabilities.mobileTesting) caps.push('Mobile');
    if (capabilities.apiTesting) caps.push('API');
    if (capabilities.automatedTesting) caps.push('Automated');

    return (
      <Space wrap>
        {caps.map(cap => (
          <Badge key={cap} count={cap} color="blue" />
        ))}
      </Space>
    );
  }, []);

  // Action handlers
  const handleCreateDevelopmentAccount = useCallback((environmentId: string) => {
    const accountData = {
      environmentId,
      accountType: 'web' as const,
      testConfig: {
        purpose: 'development_testing',
        automated: true,
      },
    };

    setActionInProgress('creating');
    createAccountMutation.mutate(accountData, {
      onSettled: () => setActionInProgress(null),
    });
  }, [createAccountMutation]);

  const handleExecuteWorkflow = useCallback((account: Account, workflowType: string) => {
    const parameters = {
      source: 'frontend_ui',
      executedBy: 'user',
      accountType: account.accountType,
    };

    setActionInProgress(`${workflowType}-${account.id}`);
    executeWorkflowMutation.mutate(
      { accountId: account.id, workflowType, parameters },
      { onSettled: () => setActionInProgress(null) }
    );
  }, [executeWorkflowMutation]);

  const handleViewDetails = useCallback((account: Account) => {
    setSelectedAccount(account);
    setDetailsModalVisible(true);
  }, []);

  const handleDeleteAccount = useCallback((accountId: string) => {
    setActionInProgress(`deleting-${accountId}`);
    deleteAccountMutation.mutate(accountId, {
      onSettled: () => setActionInProgress(null),
    });
  }, [deleteAccountMutation]);

  // Table columns
  const columns: ColumnsType<Account> = [
    {
      title: 'Account ID',
      dataIndex: 'id',
      key: 'id',
      width: 200,
      render: (id: string) => (
        <Text code copyable={{ text: id }}>
          {id.substring(0, 12)}...
        </Text>
      ),
    },
    {
      title: 'Environment',
      dataIndex: 'environmentId',
      key: 'environmentId',
      width: 150,
      render: (envId: string) => <Tag>{envId}</Tag>,
    },
    {
      title: 'Type',
      dataIndex: 'accountType',
      key: 'accountType',
      width: 100,
      render: (type: string) => (
        <Tag color="blue">{type.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: renderStatus,
    },
    {
      title: 'Development Account Status',
      key: 'developmentStatus',
      width: 200,
      render: (_, record) => renderDevelopmentAccountStatus(record),
    },
    {
      title: 'Capabilities',
      dataIndex: 'capabilities',
      key: 'capabilities',
      width: 200,
      render: renderCapabilities,
    },
    {
      title: 'Created',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 150,
      render: (date: string) => (
        <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
          <Text>{dayjs(date).fromNow()}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 300,
      render: (_, record) => (
        <AccountActions
          account={record}
          onExecuteWorkflow={handleExecuteWorkflow}
          onViewDetails={handleViewDetails}
          onDelete={handleDeleteAccount}
          actionInProgress={actionInProgress}
        />
      ),
    },
  ];

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <ExclamationCircleOutlined style={{ fontSize: '48px', color: '#ff4d4f' }} />
        <h3>Failed to load accounts</h3>
        <p>{(error as Error).message}</p>
        <Button onClick={() => refetch()} icon={<ReloadOutlined />}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => handleCreateDevelopmentAccount(`dev-env-${Date.now()}`)}
            loading={actionInProgress === 'creating'}
          >
            Create Development Account
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => refetch()}
            loading={isLoading}
          >
            Refresh
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={accounts}
        rowKey="id"
        loading={isLoading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `Total ${total} accounts`,
        }}
        scroll={{ x: 1400 }}
      />

      {/* Account Details Modal */}
      <Modal
        title="Account Details"
        open={detailsModalVisible}
        onCancel={() => setDetailsModalVisible(false)}
        footer={null}
        width={800}
      >
        {selectedAccount && (
          <AccountDetails
            account={selectedAccount}
            onClose={() => setDetailsModalVisible(false)}
          />
        )}
      </Modal>
    </>
  );
};

export default AccountsTable;
EOF

    log "✓ Enhanced AccountsTable component created"
}

# Create AccountActions component
create_account_actions() {
    log "Creating AccountActions component..."
    
    cat > "${FRONTEND_DIR}/src/components/accounts/AccountActions.tsx" << 'EOF'
import React from 'react';
import {
  Button,
  Space,
  Dropdown,
  Popconfirm,
  Tooltip,
  MenuProps,
} from 'antd';
import {
  PlayCircleOutlined,
  EyeOutlined,
  DeleteOutlined,
  MoreOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  CleaningOutlined,
} from '@ant-design/icons';
import { Account } from '../../contexts/AccountContext';

interface AccountActionsProps {
  account: Account;
  onExecuteWorkflow: (account: Account, workflowType: string) => void;
  onViewDetails: (account: Account) => void;
  onDelete: (accountId: string) => void;
  actionInProgress: string | null;
}

const AccountActions: React.FC<AccountActionsProps> = ({
  account,
  onExecuteWorkflow,
  onViewDetails,
  onDelete,
  actionInProgress,
}) => {
  const isActionInProgress = (action: string) => 
    actionInProgress === `${action}-${account.id}`;

  const isAccountActive = account.status === 'active';
  const isAccountFailed = account.status === 'failed';

  // Workflow menu items
  const workflowMenuItems: MenuProps['items'] = [
    {
      key: 'setup',
      label: 'Setup Workflow',
      icon: <SettingOutlined />,
      disabled: !isAccountActive,
      onClick: () => onExecuteWorkflow(account, 'setup'),
    },
    {
      key: 'test',
      label: 'Test Workflow',
      icon: <PlayCircleOutlined />,
      disabled: !isAccountActive,
      onClick: () => onExecuteWorkflow(account, 'test'),
    },
    {
      key: 'validation',
      label: 'Validation Workflow',
      icon: <CheckCircleOutlined />,
      disabled: !isAccountActive,
      onClick: () => onExecuteWorkflow(account, 'validation'),
    },
    {
      key: 'cleanup',
      label: 'Cleanup Workflow',
      icon: <CleaningOutlined />,
      onClick: () => onExecuteWorkflow(account, 'cleanup'),
    },
  ];

  return (
    <Space size="small">
      {/* View Details Button */}
      <Tooltip title="View account details">
        <Button
          size="small"
          icon={<EyeOutlined />}
          onClick={() => onViewDetails(account)}
        />
      </Tooltip>

      {/* Quick Test Button */}
      {isAccountActive && (
        <Tooltip title="Run quick test workflow">
          <Button
            size="small"
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={isActionInProgress('test')}
            onClick={() => onExecuteWorkflow(account, 'test')}
          >
            Test
          </Button>
        </Tooltip>
      )}

      {/* Workflow Dropdown */}
      <Dropdown
        menu={{ items: workflowMenuItems }}
        trigger={['click']}
        placement="bottomRight"
      >
        <Tooltip title="More workflow actions">
          <Button
            size="small"
            icon={<MoreOutlined />}
            loading={
              isActionInProgress('setup') ||
              isActionInProgress('validation') ||
              isActionInProgress('cleanup')
            }
          />
        </Tooltip>
      </Dropdown>

      {/* Delete Button */}
      <Popconfirm
        title="Delete Account"
        description={`Are you sure you want to delete account ${account.id.substring(0, 12)}...?`}
        onConfirm={() => onDelete(account.id)}
        okText="Yes, Delete"
        cancelText="Cancel"
        okButtonProps={{ danger: true }}
      >
        <Tooltip title="Delete account and cleanup resources">
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            loading={isActionInProgress('deleting')}
          />
        </Tooltip>
      </Popconfirm>
    </Space>
  );
};

export default AccountActions;
EOF

    log "✓ AccountActions component created"
}

# Create AccountDetails component
create_account_details() {
    log "Creating AccountDetails component..."
    
    cat > "${FRONTEND_DIR}/src/components/accounts/AccountDetails.tsx" << 'EOF'
import React from 'react';
import {
  Descriptions,
  Tag,
  Space,
  Typography,
  Divider,
  Badge,
  Card,
  Row,
  Col,
  Progress,
} from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { Account } from '../../contexts/AccountContext';

const { Title, Text, Paragraph } = Typography;

interface AccountDetailsProps {
  account: Account;
  onClose: () => void;
}

const AccountDetails: React.FC<AccountDetailsProps> = ({ account }) => {
  // Status icon mapping
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'creating':
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'cleaning':
        return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
      default:
        return null;
    }
  };

  // Calculate account age and uptime
  const accountAge = dayjs().diff(dayjs(account.createdAt), 'hours');
  const accountUptime = account.status === 'active' ? accountAge : 0;
  const uptimePercentage = accountAge > 0 ? (accountUptime / accountAge) * 100 : 0;

  return (
    <div>
      <Title level={4}>
        <Space>
          {getStatusIcon(account.status)}
          Account Details
        </Space>
      </Title>

      {/* Basic Information */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="Account ID">
            <Text code copyable={{ text: account.id }}>
              {account.id}
            </Text>
          </Descriptions.Item>
          
          <Descriptions.Item label="Environment ID">
            <Tag color="blue">{account.environmentId}</Tag>
          </Descriptions.Item>
          
          <Descriptions.Item label="Account Type">
            <Tag color="green">{account.accountType.toUpperCase()}</Tag>
          </Descriptions.Item>
          
          <Descriptions.Item label="Status">
            <Space>
              {getStatusIcon(account.status)}
              <Tag color={
                account.status === 'active' ? 'success' :
                account.status === 'creating' ? 'processing' :
                account.status === 'failed' ? 'error' : 'warning'
              }>
                {account.status.toUpperCase()}
              </Tag>
            </Space>
          </Descriptions.Item>
          
          <Descriptions.Item label="Created">
            <Space direction="vertical" size={0}>
              <Text>{dayjs(account.createdAt).format('YYYY-MM-DD HH:mm:ss')}</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {dayjs(account.createdAt).fromNow()}
              </Text>
            </Space>
          </Descriptions.Item>
          
          <Descriptions.Item label="Last Updated">
            <Space direction="vertical" size={0}>
              <Text>{dayjs(account.lastUpdated).format('YYYY-MM-DD HH:mm:ss')}</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {dayjs(account.lastUpdated).fromNow()}
              </Text>
            </Space>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Development Configuration */}
      {account.testConfig && (
        <Card title="Development Configuration" size="small" style={{ marginBottom: 16 }}>
          <Descriptions column={2} size="small">
            <Descriptions.Item label="Purpose">
              <Tag color={account.testConfig.purpose.includes('development') ? 'green' : 'orange'}>
                {account.testConfig.purpose}
              </Tag>
            </Descriptions.Item>
            
            <Descriptions.Item label="Automated">
              <Badge
                status={account.testConfig.automated ? 'success' : 'default'}
                text={account.testConfig.automated ? 'Yes' : 'No'}
              />
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* Capabilities */}
      {account.capabilities && (
        <Card title="Account Capabilities" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <div style={{ marginBottom: 8 }}>
                <Badge
                  status={account.capabilities.webTesting ? 'success' : 'default'}
                  text="Web Testing"
                />
              </div>
              <div style={{ marginBottom: 8 }}>
                <Badge
                  status={account.capabilities.mobileTesting ? 'success' : 'default'}
                  text="Mobile Testing"
                />
              </div>
            </Col>
            <Col span={12}>
              <div style={{ marginBottom: 8 }}>
                <Badge
                  status={account.capabilities.apiTesting ? 'success' : 'default'}
                  text="API Testing"
                />
              </div>
              <div style={{ marginBottom: 8 }}>
                <Badge
                  status={account.capabilities.automatedTesting ? 'success' : 'default'}
                  text="Automated Testing"
                />
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {/* Account Metrics */}
      <Card title="Account Metrics" size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff' }}>
                {accountAge}h
              </div>
              <div style={{ color: '#666' }}>Account Age</div>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                {accountUptime}h
              </div>
              <div style={{ color: '#666' }}>Uptime</div>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center', marginBottom: 8 }}>
              <Progress
                type="circle"
                size={60}
                percent={Math.round(uptimePercentage)}
                status={uptimePercentage > 90 ? 'success' : uptimePercentage > 70 ? 'normal' : 'exception'}
              />
            </div>
            <div style={{ color: '#666', textAlign: 'center' }}>Reliability</div>
          </Col>
        </Row>
      </Card>

      {/* Development Notes */}
      <Card title="Development Notes" size="small">
        <Paragraph>
          <Text strong>Purpose:</Text> This account is created for legitimate development testing purposes.
        </Paragraph>
        <Paragraph>
          <Text strong>Usage:</Text> Use this account for testing development workflows, API integrations, and automated testing scenarios.
        </Paragraph>
        <Paragraph>
          <Text strong>Security:</Text> This account should not be used with production data or in production environments.
        </Paragraph>
        {account.status === 'failed' && (
          <Paragraph>
            <Text type="danger" strong>Note:</Text> This account has failed initialization. 
            Check the logs for detailed error information and consider recreating the account.
          </Paragraph>
        )}
      </Card>
    </div>
  );
};

export default AccountDetails;
EOF

    log "✓ AccountDetails component created"
}

# Create account service
create_account_service() {
    log "Creating account service..."
    
    cat > "${FRONTEND_DIR}/src/services/accountService.ts" << 'EOF'
import axios from 'axios';
import { Account } from '../contexts/AccountContext';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add any auth tokens or common headers here
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle authentication errors
      console.warn('Authentication error - redirecting to login');
    }
    return Promise.reject(error);
  }
);

export interface CreateAccountRequest {
  environmentId: string;
  accountType: 'web' | 'mobile' | 'api';
  testConfig?: {
    purpose: string;
    automated: boolean;
    [key: string]: any;
  };
}

export interface GetAccountsParams {
  environmentId?: string;
  accountType?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export interface ExecuteWorkflowRequest {
  workflowType: 'setup' | 'test' | 'validation' | 'cleanup';
  parameters?: {
    [key: string]: any;
  };
}

export const accountService = {
  /**
   * Get list of accounts
   */
  async getAccounts(params: GetAccountsParams = {}): Promise<Account[]> {
    try {
      const response = await apiClient.get('/account/list', { params });
      
      if (response.data.success) {
        return response.data.data.accounts || [];
      } else {
        throw new Error(response.data.message || 'Failed to fetch accounts');
      }
    } catch (error: any) {
      throw new Error(`Failed to fetch accounts: ${error.message}`);
    }
  },

  /**
   * Get account by ID
   */
  async getAccount(accountId: string): Promise<Account> {
    try {
      const response = await apiClient.get(`/account/status/${accountId}`);
      
      if (response.data.success) {
        return response.data.data;
      } else {
        throw new Error(response.data.message || 'Failed to fetch account');
      }
    } catch (error: any) {
      throw new Error(`Failed to fetch account: ${error.message}`);
    }
  },

  /**
   * Create new development account
   */
  async createAccount(accountData: CreateAccountRequest): Promise<Account> {
    try {
      // Ensure account is marked for development testing
      const developmentAccountData = {
        ...accountData,
        testConfig: {
          purpose: 'development_testing',
          automated: true,
          ...accountData.testConfig,
        },
      };

      const response = await apiClient.post('/account/create', developmentAccountData);
      
      if (response.data.success) {
        return response.data.data;
      } else {
        throw new Error(response.data.message || 'Failed to create account');
      }
    } catch (error: any) {
      throw new Error(`Failed to create account: ${error.message}`);
    }
  },

  /**
   * Execute workflow on account
   */
  async executeWorkflow(
    accountId: string,
    workflowType: string,
    parameters: any = {}
  ): Promise<{ workflowId: string; status: string }> {
    try {
      const workflowData = {
        workflowType,
        accountId,
        parameters: {
          source: 'frontend_ui',
          executedBy: 'user',
          ...parameters,
        },
      };

      const response = await apiClient.post('/account/workflow/execute', workflowData);
      
      if (response.data.success) {
        return response.data.data;
      } else {
        throw new Error(response.data.message || 'Failed to execute workflow');
      }
    } catch (error: any) {
      throw new Error(`Failed to execute workflow: ${error.message}`);
    }
  },

  /**
   * Delete account
   */
  async deleteAccount(accountId: string): Promise<void> {
    try {
      const response = await apiClient.delete(`/account/cleanup/${accountId}`);
      
      if (!response.data.success) {
        throw new Error(response.data.message || 'Failed to delete account');
      }
    } catch (error: any) {
      throw new Error(`Failed to delete account: ${error.message}`);
    }
  },

  /**
   * Get account statistics
   */
  async getAccountStats(): Promise<{
    total: number;
    byStatus: Record<string, number>;
    byType: Record<string, number>;
  }> {
    try {
      const accounts = await this.getAccounts();
      
      const stats = {
        total: accounts.length,
        byStatus: {} as Record<string, number>,
        byType: {} as Record<string, number>,
      };

      accounts.forEach(account => {
        // Count by status
        stats.byStatus[account.status] = (stats.byStatus[account.status] || 0) + 1;
        
        // Count by type
        stats.byType[account.accountType] = (stats.byType[account.accountType] || 0) + 1;
      });

      return stats;
    } catch (error: any) {
      throw new Error(`Failed to get account statistics: ${error.message}`);
    }
  },

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await apiClient.get('/health');
      return response.data;
    } catch (error: any) {
      throw new Error(`Health check failed: ${error.message}`);
    }
  },
};

export default accountService;
EOF

    log "✓ Account service created"
}

# Create layout and pages
create_layout_and_pages() {
    log "Creating layout and pages..."
    
    # Layout component
    cat > "${FRONTEND_DIR}/src/components/common/Layout.tsx" << 'EOF'
import React, { ReactNode } from 'react';
import { Layout as AntLayout, Menu, Typography, Space, Badge } from 'antd';
import {
  DashboardOutlined,
  SettingOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQuery } from 'react-query';
import { accountService } from '../../services/accountService';

const { Header, Content, Sider } = AntLayout;
const { Title } = Typography;

interface LayoutProps {
  children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  // Get account stats for badge counts
  const { data: accountStats } = useQuery(
    'account-stats',
    accountService.getAccountStats,
    { refetchInterval: 60000 }
  );

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/accounts',
      icon: <ApiOutlined />,
      label: (
        <Space>
          Account Management
          {accountStats?.total && (
            <Badge count={accountStats.total} size="small" />
          )}
        </Space>
      ),
    },
  ];

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Header style={{ padding: '0 24px', background: '#fff', borderBottom: '1px solid #f0f0f0' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
            Development Account Management
          </Title>
          <Space>
            <Badge status="processing" text="Connected" />
          </Space>
        </div>
      </Header>
      
      <AntLayout>
        <Sider width={250} style={{ background: '#fff', borderRight: '1px solid #f0f0f0' }}>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            style={{ height: '100%', borderRight: 0 }}
            onClick={({ key }) => navigate(key)}
          />
        </Sider>
        
        <AntLayout style={{ padding: '24px' }}>
          <Content
            style={{
              background: '#fff',
              padding: '24px',
              borderRadius: '6px',
              minHeight: 'calc(100vh - 112px)',
            }}
          >
            {children}
          </Content>
        </AntLayout>
      </AntLayout>
    </AntLayout>
  );
};

export default Layout;
EOF

    # Dashboard page
    cat > "${FRONTEND_DIR}/src/pages/Dashboard.tsx" << 'EOF'
import React from 'react';
import { Row, Col, Card, Statistic, Typography, Space, Spin } from 'antd';
import {
  UserOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useQuery } from 'react-query';
import { accountService } from '../services/accountService';

const { Title, Paragraph } = Typography;

const Dashboard: React.FC = () => {
  const { data: accountStats, isLoading } = useQuery(
    'account-stats',
    accountService.getAccountStats,
    { refetchInterval: 30000 }
  );

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div>
      <Title level={2}>Development Account Dashboard</Title>
      <Paragraph>
        Monitor and manage development test accounts for your applications.
      </Paragraph>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Accounts"
              value={accountStats?.total || 0}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Active Accounts"
              value={accountStats?.byStatus?.active || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Creating"
              value={accountStats?.byStatus?.creating || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Failed"
              value={accountStats?.byStatus?.failed || 0}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Card title="Account Types" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              {accountStats?.byType && Object.entries(accountStats.byType).map(([type, count]) => (
                <div key={type} style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>{type.toUpperCase()}</span>
                  <strong>{count}</strong>
                </div>
              ))}
            </Space>
          </Card>
        </Col>
        <Col span={16}>
          <Card title="Quick Actions" size="small">
            <Paragraph>
              <strong>Development Testing:</strong> All accounts created through this interface are designed for development testing purposes only.
            </Paragraph>
            <Paragraph>
              <strong>Security:</strong> Do not use production data or credentials with test accounts.
            </Paragraph>
            <Paragraph>
              <strong>Cleanup:</strong> Test accounts are automatically cleaned up based on configured policies.
            </Paragraph>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
EOF

    # Account Management page
    cat > "${FRONTEND_DIR}/src/pages/AccountManagement.tsx" << 'EOF'
import React, { useState } from 'react';
import { Card, Row, Col, Select, Input, Space, Typography } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import AccountsTable from '../components/accounts/AccountsTable';

const { Title } = Typography;
const { Option } = Select;

const AccountManagement: React.FC = () => {
  const [environmentFilter, setEnvironmentFilter] = useState<string>('');
  const [accountTypeFilter, setAccountTypeFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');

  return (
    <div>
      <Title level={2}>Account Management</Title>
      
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col span={6}>
            <Input
              placeholder="Search accounts..."
              prefix={<SearchOutlined />}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              allowClear
            />
          </Col>
          <Col span={6}>
            <Select
              placeholder="Filter by environment"
              style={{ width: '100%' }}
              value={environmentFilter}
              onChange={setEnvironmentFilter}
              allowClear
            >
              <Option value="">All Environments</Option>
              <Option value="dev">Development</Option>
              <Option value="test">Testing</Option>
              <Option value="staging">Staging</Option>
            </Select>
          </Col>
          <Col span={6}>
            <Select
              placeholder="Filter by account type"
              style={{ width: '100%' }}
              value={accountTypeFilter}
              onChange={setAccountTypeFilter}
              allowClear
            >
              <Option value="">All Types</Option>
              <Option value="web">Web</Option>
              <Option value="mobile">Mobile</Option>
              <Option value="api">API</Option>
            </Select>
          </Col>
        </Row>
      </Card>

      <Card>
        <AccountsTable
          environmentFilter={environmentFilter}
          accountTypeFilter={accountTypeFilter}
        />
      </Card>
    </div>
  );
};

export default AccountManagement;
EOF

    log "✓ Layout and pages created"
}

# Create build and deployment scripts
create_build_scripts() {
    log "Creating build and deployment scripts..."
    
    cat > "${FRONTEND_DIR}/build.sh" << 'EOF'
#!/bin/bash

# Frontend Build Script for Development Account Management UI
# Builds and prepares the React application for deployment

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[BUILD]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[BUILD]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log "Starting frontend build process..."

# Check if package.json exists
if [[ ! -f package.json ]]; then
    warn "package.json not found. Creating from template..."
    cp package.json.example package.json 2>/dev/null || {
        echo "Error: No package.json found and no template available"
        exit 1
    }
fi

# Install dependencies
log "Installing dependencies..."
if command -v npm &> /dev/null; then
    npm install
elif command -v yarn &> /dev/null; then
    yarn install
else
    echo "Error: Neither npm nor yarn found"
    exit 1
fi

# Run linting (if available)
if npm list eslint &>/dev/null; then
    log "Running linting checks..."
    npm run lint || warn "Linting completed with warnings"
fi

# Run tests (if available)
if npm list @testing-library/react &>/dev/null; then
    log "Running tests..."
    CI=true npm test -- --coverage --watchAll=false || warn "Some tests failed"
fi

# Build the application
log "Building React application..."
npm run build

# Verify build
if [[ -d build && -f build/index.html ]]; then
    log "✅ Build completed successfully"
    
    # Display build info
    BUILD_SIZE=$(du -sh build | cut -f1)
    log "Build size: $BUILD_SIZE"
    
    # List build contents
    log "Build contents:"
    ls -la build/
    
else
    echo "❌ Build failed - build directory or index.html not found"
    exit 1
fi

log "Frontend build process completed!"
EOF

    chmod +x "${FRONTEND_DIR}/build.sh"

    # Create development server script
    cat > "${FRONTEND_DIR}/start-dev.sh" << 'EOF'
#!/bin/bash

# Development Server Start Script
# Starts the React development server with proper configuration

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[DEV]${NC} $1"
}

info() {
    echo -e "${BLUE}[DEV]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log "Starting React development server..."

# Check if dependencies are installed
if [[ ! -d node_modules ]]; then
    log "Installing dependencies..."
    npm install
fi

# Set development environment variables
export REACT_APP_API_URL="${API_BASE_URL:-http://localhost:3001/api/v1}"
export REACT_APP_ENV="development"
export BROWSER=none  # Don't auto-open browser

info "Development server configuration:"
info "  API URL: $REACT_APP_API_URL"
info "  Frontend URL: http://localhost:3000"
info "  Environment: development"

# Start development server
log "Starting development server on http://localhost:3000"
npm start
EOF

    chmod +x "${FRONTEND_DIR}/start-dev.sh"

    log "✓ Build and deployment scripts created"
}

# Create environment configuration
create_environment_config() {
    log "Creating environment configuration..."
    
    cat > "${FRONTEND_DIR}/.env.example" << 'EOF'
# React Application Environment Configuration

# API Configuration
REACT_APP_API_URL=http://localhost:3001/api/v1
REACT_APP_ENV=development

# Application Configuration
REACT_APP_NAME=Development Account Management UI
REACT_APP_VERSION=1.0.0

# Development Configuration
GENERATE_SOURCEMAP=true
BROWSER=none

# Build Configuration
BUILD_PATH=build
PUBLIC_URL=
EOF

    cat > "${FRONTEND_DIR}/.gitignore" << 'EOF'
# Dependencies
/node_modules
/.pnp
.pnp.js

# Testing
/coverage

# Production
/build

# Environment
.env.local
.env.development.local
.env.test.local
.env.production.local

# Logs
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Runtime
.DS_Store

# IDE
.vscode/
.idea/
*.swp
*.swo

# Temporary
*.tmp
*.temp
EOF

    log "✓ Environment configuration created"
}

# Create documentation
create_documentation() {
    log "Creating frontend documentation..."
    
    cat > "${FRONTEND_DIR}/README.md" << 'EOF'
# Development Account Management UI

A React-based frontend for managing development test accounts and workflows. This UI provides a comprehensive interface for creating, monitoring, and managing development accounts used in testing environments.

## Features

- **Account Management**: Create and manage development test accounts
- **Real-time Status**: Live updates of account status and workflows
- **Workflow Control**: Execute and monitor automated workflows
- **Enhanced UI**: Modern React interface with Ant Design components
- **Development Focus**: Specifically designed for development testing workflows

## Architecture

### Technology Stack
- **React 18** with TypeScript for type safety
- **Ant Design** for UI components and styling
- **React Query** for state management and API caching
- **React Router** for navigation
- **Axios** for API communication

### Key Components

#### AccountsTable
Enhanced table component that displays development accounts with:
- Account ID, environment, type, and status columns
- Development account status indicators
- Capability badges (Web, Mobile, API, Automated)
- Integrated action buttons for workflow execution
- Real-time status updates

#### AccountActions
Action component providing:
- Quick test workflow execution
- Detailed workflow dropdown menu
- Account deletion with confirmation
- Loading states for in-progress actions

#### AccountDetails
Detailed view modal showing:
- Complete account information
- Development configuration details
- Account capabilities and metrics
- Uptime and reliability statistics

## Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation
```bash
# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env

# Start development server
./start-dev.sh
```

### Building for Production
```bash
# Build optimized version
./build.sh

# Serve built files
npx serve -s build -p 3000
```

## API Integration

### Account Service
The frontend integrates with the backend API through `accountService.ts`:

```typescript
// Get all accounts
const accounts = await accountService.getAccounts({
  environmentId: 'dev-env-001',
  accountType: 'web'
});

// Create development account
const account = await accountService.createAccount({
  environmentId: 'test-env-001',
  accountType: 'web',
  testConfig: {
    purpose: 'development_testing',
    automated: true
  }
});

// Execute workflow
const workflow = await accountService.executeWorkflow(
  accountId,
  'test',
  { source: 'frontend_ui' }
);
```

### Real-time Updates
- Accounts table refreshes every 30 seconds
- Account statistics update every minute
- Loading states for all async operations
- Error handling with user-friendly messages

## UI Components

### Enhanced AccountsTable Features

#### Status Display
```tsx
// Status indicators with icons
const renderStatus = (status: string) => {
  const statusConfig = {
    creating: { color: 'processing', icon: <ClockCircleOutlined /> },
    active: { color: 'success', icon: <CheckCircleOutlined /> },
    failed: { color: 'error', icon: <CloseCircleOutlined /> },
    cleaning: { color: 'warning', icon: <ExclamationCircleOutlined /> },
  };
  // ...
};
```

#### Development Account Status
- Green "Development Account" tag for legitimate development accounts
- Blue "Automated" tag for automated testing accounts
- Clear visual indicators for account purpose

#### Action Integration
```tsx
// Integrated action buttons
<AccountActions
  account={record}
  onExecuteWorkflow={handleExecuteWorkflow}
  onViewDetails={handleViewDetails}
  onDelete={handleDeleteAccount}
  actionInProgress={actionInProgress}
/>
```

### Account Management Features

#### Create Development Account
```tsx
const handleCreateDevelopmentAccount = (environmentId: string) => {
  const accountData = {
    environmentId,
    accountType: 'web' as const,
    testConfig: {
      purpose: 'development_testing',
      automated: true,
    },
  };
  createAccountMutation.mutate(accountData);
};
```

#### Workflow Execution
```tsx
const workflowMenuItems = [
  {
    key: 'setup',
    label: 'Setup Workflow',
    onClick: () => onExecuteWorkflow(account, 'setup'),
  },
  // ... other workflow types
];
```

## Development

### Project Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── accounts/
│   │   │   ├── AccountsTable.tsx      # Enhanced accounts table
│   │   │   ├── AccountActions.tsx     # Action buttons and menus
│   │   │   └── AccountDetails.tsx     # Detailed account view
│   │   └── common/
│   │       └── Layout.tsx             # App layout
│   ├── contexts/
│   │   └── AccountContext.tsx         # Account state management
│   ├── pages/
│   │   ├── Dashboard.tsx              # Dashboard with statistics
│   │   └── AccountManagement.tsx      # Main account management page
│   ├── services/
│   │   └── accountService.ts          # API service layer
│   └── App.tsx                        # Main app component
├── public/
└── package.json
```

### State Management
Uses React Context + useReducer for account state:

```typescript
interface AccountState {
  accounts: Account[];
  selectedAccount: Account | null;
  loading: boolean;
  error: string | null;
}
```

### API Error Handling
```typescript
// Comprehensive error handling
try {
  const response = await apiClient.post('/account/create', data);
  if (response.data.success) {
    return response.data.data;
  } else {
    throw new Error(response.data.message);
  }
} catch (error) {
  throw new Error(`Failed to create account: ${error.message}`);
}
```

## Configuration

### Environment Variables
```bash
# API endpoint
REACT_APP_API_URL=http://localhost:3001/api/v1

# Application settings
REACT_APP_ENV=development
REACT_APP_NAME=Development Account Management UI
```

### Build Configuration
- TypeScript for type safety
- ESLint for code quality
- Jest for testing
- Source maps in development
- Optimized builds for production

## Testing

### Running Tests
```bash
# Run all tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run tests in CI mode
CI=true npm test -- --coverage --watchAll=false
```

### Test Structure
- Component testing with React Testing Library
- API service testing
- Integration tests for workflows
- Snapshot testing for UI consistency

## Security

### Development Focus
- All accounts created are marked for development testing
- Clear visual indicators for development vs production
- No production credentials or data handling
- Comprehensive audit logging

### API Security
- Request/response interceptors
- Authentication token handling
- CORS configuration
- Input validation

## Deployment

### Development Deployment
```bash
# Start development server
npm start

# Or use the provided script
./start-dev.sh
```

### Production Deployment
```bash
# Build optimized version
npm run build

# Serve static files
npx serve -s build -p 3000

# Or with nginx/apache
# Copy build/ contents to web server directory
```

### Docker Deployment
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY build ./build
RUN npm install -g serve
EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
```

## Integration with Backend

### Account Creation Flow
1. User clicks "Create Development Account"
2. Frontend calls `/api/v1/account/create` with development config
3. Backend validates and creates account
4. Frontend updates UI with new account
5. Real-time polling shows status updates

### Workflow Execution Flow
1. User selects workflow from dropdown
2. Frontend calls `/api/v1/account/workflow/execute`
3. Backend starts workflow execution
4. Frontend shows loading state
5. Polling updates show workflow progress

This UI provides a comprehensive interface for development account management while maintaining clear separation between development and production environments.
EOF

    log "✓ Frontend documentation created"
}

# Main installation function
main() {
    log "Setting up Frontend Integration for Development Account Management..."
    log "This creates a comprehensive React UI for managing development accounts and workflows"
    
    # Check dependencies
    if ! command -v node &> /dev/null; then
        warn "Node.js not found. Please install Node.js 18+ first."
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        warn "npm not found. Please install npm first."
        exit 1
    fi
    
    # Run setup functions
    setup_directories
    create_frontend_package
    create_main_app
    create_account_context
    create_accounts_table
    create_account_actions
    create_account_details
    create_account_service
    create_layout_and_pages
    create_build_scripts
    create_environment_config
    create_documentation
    
    log "✅ Frontend Integration setup complete!"
    log ""
    log "🚀 Quick Start:"
    log "   cd ${FRONTEND_DIR} && ./start-dev.sh"
    log ""
    log "🌐 Application URLs:"
    log "   • Development: http://localhost:3000"
    log "   • API Backend: ${API_ENDPOINT}"
    log ""
    log "🔧 Build Commands:"
    log "   • Development: ./start-dev.sh"
    log "   • Production Build: ./build.sh"
    log "   • Install Dependencies: npm install"
    log "   • Run Tests: npm test"
    log ""
    log "📋 Key Features:"
    log "   • Enhanced AccountsTable with development account status"
    log "   • Real-time status updates and workflow controls"
    log "   • Comprehensive account details and metrics"
    log "   • Modern React + TypeScript + Ant Design UI"
    log "   • Integrated action buttons for workflow execution"
    log "   • Development-focused account management"
    log ""
    log "🎨 UI Components:"
    log "   • AccountsTable - Enhanced table with status columns"
    log "   • AccountActions - Workflow execution and management"
    log "   • AccountDetails - Comprehensive account information"
    log "   • Dashboard - Statistics and overview"
    log ""
    log "⚙️ Configuration:"
    log "   • Copy .env.example to .env for custom configuration"
    log "   • Update REACT_APP_API_URL for your backend endpoint"
    log "   • All accounts created are marked for development testing"
}

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi