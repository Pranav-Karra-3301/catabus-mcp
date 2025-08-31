# 🚀 Deployment Guide for CATA Bus MCP Server

## FastMCP Cloud Deployment

### Prerequisites
1. FastMCP Cloud account at https://fastmcp.cloud
2. GitHub repository with this code
3. Python 3.11+

### Quick Deploy

1. **Push to GitHub:**
```bash
git remote add origin https://github.com/yourusername/catabus-mcp.git
git push -u origin main
```

2. **Deploy to FastMCP Cloud:**
```bash
# Install FastMCP CLI
pip install fastmcp-cli

# Login to FastMCP Cloud
fastmcp login

# Deploy from current directory
fastmcp deploy

# Or deploy from GitHub
fastmcp deploy --github yourusername/catabus-mcp
```

3. **Monitor deployment:**
```bash
fastmcp logs catabus-mcp
fastmcp status catabus-mcp
```

## Configuration

The `fastmcp.toml` file contains all deployment configuration:

- **Memory**: 512MB (sufficient for GTFS data)
- **Timeout**: 30 seconds per request
- **Caching**: 24-hour TTL for static GTFS data
- **Health check**: Every 60 seconds

## Environment Variables

Set these in FastMCP Cloud dashboard if needed:

```env
TZ=America/New_York  # CATA operates in Eastern Time
LOG_LEVEL=INFO       # Logging verbosity
```

## Testing Deployment

Once deployed, test with:

```bash
# List available tools
fastmcp test catabus-mcp tools/list

# Test a specific tool
fastmcp test catabus-mcp list_routes_tool

# Health check
curl https://your-deployment.fastmcp.cloud/health
```

## Monitoring

### Logs
```bash
fastmcp logs catabus-mcp --follow
```

### Metrics
- Check FastMCP Cloud dashboard for:
  - Request rate
  - Response times
  - Error rate
  - Memory usage

### Alerts
Set up alerts in FastMCP Cloud for:
- Error rate > 5%
- Response time > 2s
- Memory usage > 80%

## Scaling

The server automatically scales based on load:
- Min instances: 1
- Max instances: 10
- Scale up at 70% CPU
- Scale down at 30% CPU

## Troubleshooting

### Common Issues

1. **"No routes loaded"**
   - Check GTFS feed URL is accessible
   - Verify cache directory permissions
   - Check logs for download errors

2. **"No real-time data"**
   - CATA real-time feeds may be temporarily down
   - Check network connectivity
   - Verify 15-second polling interval

3. **"High memory usage"**
   - Normal with full GTFS data (~50MB)
   - Consider increasing memory to 1GB if needed

### Debug Mode

Enable debug logging:
```bash
fastmcp env set LOG_LEVEL=DEBUG
fastmcp restart catabus-mcp
```

## Local Development

Run locally before deploying:

```bash
# Install dependencies
pip install -e .

# Run server
python -m catabus_mcp.server_v2

# Or with FastMCP CLI
fastmcp run src/catabus_mcp/server_v2.py:mcp
```

## CI/CD

GitHub Actions automatically:
1. Run tests on push
2. Lint and type check
3. Deploy to FastMCP Cloud on main branch (if configured)

To enable auto-deploy:
1. Add `FASTMCP_API_KEY` to GitHub secrets
2. Uncomment deploy step in `.github/workflows/ci.yml`

## Support

- FastMCP Cloud docs: https://docs.fastmcp.cloud
- CATA Developer Tools: https://catabus.com/developer-tools/
- Issues: https://github.com/yourusername/catabus-mcp/issues