/**
 * PiMeet Dashboard Backend
 *
 * Main entry point for the management dashboard API server.
 */

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import compression from 'compression';
import { createServer } from 'http';
import { config } from 'dotenv';

import { logger } from './services/logger';
import { initDatabase } from './models';
import { WebSocketServer } from './websocket/server';
import { deviceRouter } from './routes/devices';
import { authRouter } from './routes/auth';
import { metricsRouter } from './routes/metrics';
import { provisioningRouter } from './routes/provisioning';
import { errorHandler } from './middleware/errorHandler';
import { authMiddleware } from './middleware/auth';

// Load environment variables
config();

const PORT = process.env.PORT || 3001;
const HOST = process.env.HOST || '0.0.0.0';

async function main() {
  logger.info('Starting PiMeet Dashboard Backend...');

  // Initialize database
  await initDatabase();
  logger.info('Database initialized');

  // Create Express app
  const app = express();

  // Middleware
  app.use(helmet());
  app.use(cors({
    origin: process.env.CORS_ORIGIN || '*',
    credentials: true,
  }));
  app.use(compression());
  app.use(morgan('combined', { stream: { write: (msg) => logger.http(msg.trim()) } }));
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));

  // Health check (unauthenticated)
  app.get('/health', (req, res) => {
    res.json({
      status: 'healthy',
      version: process.env.npm_package_version || '2.0.0-dev',
      timestamp: new Date().toISOString(),
    });
  });

  // API routes
  app.use('/api/auth', authRouter);
  app.use('/api/provisioning', provisioningRouter); // Token-based auth
  app.use('/api/devices', authMiddleware, deviceRouter);
  app.use('/api/metrics', authMiddleware, metricsRouter);

  // Error handling
  app.use(errorHandler);

  // 404 handler
  app.use((req, res) => {
    res.status(404).json({ error: 'Not found' });
  });

  // Create HTTP server
  const server = createServer(app);

  // Initialize WebSocket server for real-time device communication
  const wsServer = new WebSocketServer(server);
  logger.info('WebSocket server initialized');

  // Start server
  server.listen(Number(PORT), HOST, () => {
    logger.info(`Dashboard backend running on http://${HOST}:${PORT}`);
    logger.info(`WebSocket server running on ws://${HOST}:${PORT}/ws`);
  });

  // Graceful shutdown
  process.on('SIGTERM', async () => {
    logger.info('SIGTERM received, shutting down...');
    wsServer.close();
    server.close(() => {
      logger.info('Server closed');
      process.exit(0);
    });
  });

  process.on('SIGINT', async () => {
    logger.info('SIGINT received, shutting down...');
    wsServer.close();
    server.close(() => {
      logger.info('Server closed');
      process.exit(0);
    });
  });
}

main().catch((err) => {
  logger.error('Failed to start server:', err);
  process.exit(1);
});
