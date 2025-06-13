#!/usr/bin/env python3
"""
Setup script for VCBot MCP Server
"""

import os
import json
import subprocess
import sys
from pathlib import Path

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_claude_desktop_config():
    """Set up Claude Desktop configuration"""
    print("⚙️ Setting up Claude Desktop configuration...")
    
    # Claude Desktop config path
    config_dir = Path.home() / "Library" / "Application Support" / "Claude"
    config_file = config_dir / "claude_desktop_config.json"
    
    # Create config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # VCBot MCP server configuration
    vcbot_config = {
        "command": "python",
        "args": [str(Path(__file__).parent / "mcp_server" / "server.py")],
        "env": {
            "PYTHONPATH": str(Path(__file__).parent.parent),
            "DISCORD_TOKEN": "${DISCORD_TOKEN}",
            "GEMINI_API_KEY": "${GEMINI_API_KEY}",
            "MCP_AUTH_TOKEN": "${MCP_AUTH_TOKEN}"
        }
    }
    
    # Load existing config or create new one
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError:
            config = {}
    else:
        config = {}
    
    # Ensure mcpServers section exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Add VCBot server
    config["mcpServers"]["vcbot"] = vcbot_config
    
    # Write updated config
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Claude Desktop config updated: {config_file}")
        print("🔄 Please restart Claude Desktop to load the new configuration")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update Claude Desktop config: {e}")
        return False

def check_env_file():
    """Check if VCBot .env file exists"""
    print("📝 Checking VCBot environment configuration...")
    
    vcbot_env = Path(__file__).parent.parent / ".env"
    
    if vcbot_env.exists():
        print(f"✅ VCBot .env file found: {vcbot_env}")
        print("🔑 MCP server will use VCBot's existing tokens")
        return True
    else:
        print(f"⚠️  VCBot .env file not found: {vcbot_env}")
        print("💡 Make sure VCBot has a .env file with DISCORD_TOKEN and GEMINI_API_KEY")
        return False

def test_mcp_server():
    """Test the MCP server"""
    print("🧪 Testing MCP server...")
    
    server_file = Path(__file__).parent / "mcp_server" / "server.py"
    
    if not server_file.exists():
        print(f"❌ Server file not found: {server_file}")
        return False
    
    try:
        # Test import
        result = subprocess.run([
            sys.executable, "-c", 
            f"import sys; sys.path.append('{Path(__file__).parent}'); import mcp_server.server; print('✅ MCP server imports successfully')"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ MCP server imports successfully")
            return True
        else:
            print(f"❌ MCP server import failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ MCP server test timed out")
        return False
    except Exception as e:
        print(f"❌ MCP server test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up VCBot MCP Server...")
    print("=" * 50)
    
    success = True
    
    # Step 1: Install dependencies
    if not install_dependencies():
        success = False
    
    print()
    
    # Step 2: Check environment configuration
    if not check_env_file():
        success = False
    
    print()
    
    # Step 3: Test server
    if not test_mcp_server():
        success = False
    
    print()
    
    # Step 4: Setup Claude Desktop config
    if not setup_claude_desktop_config():
        success = False
    
    print()
    print("=" * 50)
    
    if success:
        print("🎉 Setup completed successfully!")
        print()
        print("📋 Next steps:")
        print("1. MCP server will use VCBot's existing .env file ✅")
        print("2. Restart Claude Desktop")
        print("3. Test the integration by asking Claude to search for bills")
        print()
        print("💡 Example usage in Claude:")
        print('   "Search for bills about healthcare"')
        print('   "Get the current economic report"')
        print('   "Check what\'s happening in house-floor"')
    else:
        print("❌ Setup encountered errors. Please check the output above.")
        print("🔧 You may need to manually complete some steps.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)