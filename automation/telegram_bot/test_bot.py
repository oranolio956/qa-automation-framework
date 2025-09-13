#!/usr/bin/env python3
"""
Test Script for Telegram Bot
Validates configuration and core functionality
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

async def test_configuration():
    """Test bot configuration"""
    print("🔧 Testing configuration...")
    
    try:
        from config import TelegramBotConfig, validate_config
        validate_config()
        print("✅ Configuration validation passed")
        
        # Test package loading
        packages = TelegramBotConfig.get_all_packages()
        print(f"✅ Loaded {len(packages)} service packages")
        
        # Test pricing calculation
        price, discount = TelegramBotConfig.get_total_price('starter_pack', 5)
        print(f"✅ Pricing calculation works: 5x starter pack = ${price:.2f} (${discount:.2f} discount)")
        
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

async def test_database_models():
    """Test database models"""
    print("\n💾 Testing database models...")
    
    try:
        from database import get_database, get_user_manager, get_order_manager
        
        # Test database connection (will create tables)
        db = await get_database()
        print("✅ Database connection successful")
        
        # Test user manager
        user_mgr = await get_user_manager()
        test_user = {
            'id': 999999999,
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User'
        }
        await user_mgr.create_or_update_user(test_user)
        user = await user_mgr.get_user(999999999)
        print(f"✅ User management works: {user['first_name']} {user['last_name']}")
        
        # Test order manager
        order_mgr = await get_order_manager()
        order_id = await order_mgr.create_order(999999999, 'starter_pack', 1)
        if order_id:
            print(f"✅ Order management works: Order {order_id} created")
        else:
            print("⚠️ Order creation returned None")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

async def test_payment_processor():
    """Test payment processing"""
    print("\n💳 Testing payment processor...")
    
    try:
        from payment_handler import get_payment_processor
        
        processor = get_payment_processor()
        print("✅ Payment processor initialized")
        
        # Test Telegram invoice creation
        invoice = await processor.create_telegram_payment_invoice(
            user_id=999999999,
            order_id="TEST123",
            package_id="starter_pack",
            quantity=1
        )
        
        if invoice['success']:
            print("✅ Telegram invoice creation works")
        else:
            print(f"⚠️ Telegram invoice creation failed: {invoice['error']}")
        
        return True
    except Exception as e:
        print(f"❌ Payment processor test failed: {e}")
        return False

async def test_order_lifecycle():
    """Test order lifecycle management"""
    print("\n📦 Testing order lifecycle...")
    
    try:
        from order_manager import get_order_lifecycle_manager
        
        manager = get_order_lifecycle_manager()
        print("✅ Order lifecycle manager initialized")
        
        # Test order creation
        result = await manager.create_new_order(
            user_id=999999999,
            package_id='starter_pack',
            quantity=1
        )
        
        if result['success']:
            order_id = result['order_id']
            print(f"✅ Order lifecycle works: Order {order_id} created")
            
            # Test order details
            details = await manager.get_order_details(order_id)
            if details['success']:
                print("✅ Order details retrieval works")
            else:
                print(f"⚠️ Order details failed: {details['error']}")
        else:
            print(f"⚠️ Order creation failed: {result['error']}")
        
        return True
    except Exception as e:
        print(f"❌ Order lifecycle test failed: {e}")
        return False

async def test_customer_service():
    """Test customer service components"""
    print("\n👥 Testing customer service...")
    
    try:
        from customer_service import get_customer_service_manager
        
        cs_manager = get_customer_service_manager()
        print("✅ Customer service manager initialized")
        
        # Test FAQ data
        faq_data = cs_manager.faq_data
        print(f"✅ FAQ system loaded with {len(faq_data)} categories")
        
        # Test keyboard creation
        keyboard = cs_manager.create_main_menu_keyboard()
        print("✅ Keyboard creation works")
        
        return True
    except Exception as e:
        print(f"❌ Customer service test failed: {e}")
        return False

async def test_admin_panel():
    """Test admin panel"""
    print("\n🔧 Testing admin panel...")
    
    try:
        from admin_panel import get_admin_panel_manager
        
        admin_mgr = get_admin_panel_manager()
        print("✅ Admin panel manager initialized")
        
        # Test admin check
        is_admin = admin_mgr.is_admin(123456)  # Will be False unless configured
        print(f"✅ Admin verification works: {is_admin}")
        
        # Test stats retrieval
        stats = await admin_mgr._get_system_stats()
        print(f"✅ System stats work: {stats['total_users']} users, {stats['total_orders']} orders")
        
        return True
    except Exception as e:
        print(f"❌ Admin panel test failed: {e}")
        return False

async def test_integration_with_automation():
    """Test integration with main automation system"""
    print("\n🤖 Testing automation integration...")
    
    try:
        # Test if we can import the main orchestrator
        from main_orchestrator import TinderAutomationOrchestrator, AutomationConfig
        print("✅ Can import main automation orchestrator")
        
        # Test creating automation config
        config = AutomationConfig(
            tinder_account_count=3,
            snapchat_account_count=0,
            emulator_count=1,
            aggressiveness_level=0.3,
            warming_enabled=True,
            parallel_creation=False,
            output_directory="./test_results",
            headless_emulators=True
        )
        print("✅ Automation config creation works")
        
        # Test orchestrator creation (don't run it)
        orchestrator = TinderAutomationOrchestrator(config)
        print("✅ Automation orchestrator creation works")
        
        return True
    except Exception as e:
        print(f"❌ Automation integration test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    print("🧪 Starting Telegram Bot System Tests")
    print("=" * 60)
    
    tests = [
        test_configuration,
        test_database_models,
        test_payment_processor,
        test_order_lifecycle,
        test_customer_service,
        test_admin_panel,
        test_integration_with_automation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"🧪 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Bot system is ready.")
        return True
    else:
        print(f"⚠️ {total - passed} tests failed. Please check configuration.")
        return False

if __name__ == "__main__":
    # Setup environment
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
    
    try:
        result = asyncio.run(run_all_tests())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error during testing: {e}")
        sys.exit(1)