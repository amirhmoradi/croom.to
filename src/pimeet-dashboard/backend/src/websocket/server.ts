/**
 * WebSocket server for real-time device communication.
 *
 * Handles:
 * - Device heartbeats and status updates
 * - Real-time metrics streaming
 * - Remote commands to devices
 * - Live meeting status updates
 */

import { Server as HttpServer } from 'http';
import WebSocket, { WebSocketServer as WSServer } from 'ws';
import { Device, Metrics } from '../models';
import { logger } from '../services/logger';

interface DeviceConnection {
  ws: WebSocket;
  deviceId: string;
  lastHeartbeat: Date;
}

interface WSMessage {
  type: string;
  payload?: any;
}

export class WebSocketServer {
  private wss: WSServer;
  private devices: Map<string, DeviceConnection> = new Map();
  private heartbeatInterval: NodeJS.Timeout;

  constructor(server: HttpServer) {
    this.wss = new WSServer({
      server,
      path: '/ws',
    });

    this.wss.on('connection', this.handleConnection.bind(this));

    // Check for stale connections every 30 seconds
    this.heartbeatInterval = setInterval(() => this.checkHeartbeats(), 30000);

    logger.info('WebSocket server started');
  }

  private async handleConnection(ws: WebSocket, req: any): Promise<void> {
    logger.info('New WebSocket connection');

    let deviceId: string | null = null;

    ws.on('message', async (data: Buffer) => {
      try {
        const message: WSMessage = JSON.parse(data.toString());
        await this.handleMessage(ws, message, (id) => {
          deviceId = id;
        });
      } catch (error) {
        logger.error('Error handling WebSocket message:', error);
        ws.send(JSON.stringify({ type: 'error', payload: { message: 'Invalid message' } }));
      }
    });

    ws.on('close', async () => {
      if (deviceId) {
        await this.handleDisconnect(deviceId);
      }
      logger.info(`WebSocket disconnected: ${deviceId || 'unknown'}`);
    });

    ws.on('error', (error) => {
      logger.error('WebSocket error:', error);
    });

    // Send welcome message
    ws.send(JSON.stringify({
      type: 'welcome',
      payload: { message: 'Connected to PiMeet Dashboard' },
    }));
  }

  private async handleMessage(
    ws: WebSocket,
    message: WSMessage,
    setDeviceId: (id: string) => void
  ): Promise<void> {
    switch (message.type) {
      case 'auth':
        await this.handleAuth(ws, message.payload, setDeviceId);
        break;

      case 'heartbeat':
        await this.handleHeartbeat(message.payload?.deviceId);
        break;

      case 'status':
        await this.handleStatus(message.payload);
        break;

      case 'metrics':
        await this.handleMetrics(message.payload);
        break;

      case 'meeting_event':
        await this.handleMeetingEvent(message.payload);
        break;

      default:
        logger.warn(`Unknown message type: ${message.type}`);
    }
  }

  private async handleAuth(
    ws: WebSocket,
    payload: { deviceId: string },
    setDeviceId: (id: string) => void
  ): Promise<void> {
    const { deviceId } = payload;

    if (!deviceId) {
      ws.send(JSON.stringify({ type: 'auth_error', payload: { message: 'Device ID required' } }));
      return;
    }

    // Verify device exists
    const device = await Device.findByPk(deviceId);
    if (!device) {
      ws.send(JSON.stringify({ type: 'auth_error', payload: { message: 'Unknown device' } }));
      return;
    }

    // Register connection
    this.devices.set(deviceId, {
      ws,
      deviceId,
      lastHeartbeat: new Date(),
    });

    setDeviceId(deviceId);

    // Update device status
    await device.update({
      status: 'online',
      lastSeen: new Date(),
    });

    logger.info(`Device ${deviceId} authenticated`);

    ws.send(JSON.stringify({
      type: 'auth_success',
      payload: { deviceId, config: device.config },
    }));
  }

  private async handleHeartbeat(deviceId?: string): Promise<void> {
    if (!deviceId) return;

    const connection = this.devices.get(deviceId);
    if (connection) {
      connection.lastHeartbeat = new Date();

      // Update device last seen
      await Device.update(
        { lastSeen: new Date() },
        { where: { id: deviceId } }
      );
    }
  }

  private async handleStatus(payload: {
    deviceId: string;
    status: 'online' | 'offline' | 'error';
    message?: string;
  }): Promise<void> {
    const { deviceId, status, message } = payload;

    await Device.update(
      { status, lastSeen: new Date() },
      { where: { id: deviceId } }
    );

    logger.info(`Device ${deviceId} status: ${status}${message ? ` - ${message}` : ''}`);
  }

  private async handleMetrics(payload: {
    deviceId: string;
    type: string;
    data: object;
  }): Promise<void> {
    const { deviceId, type, data } = payload;

    await Metrics.create({
      deviceId,
      type,
      data,
      timestamp: new Date(),
    });

    logger.debug(`Metrics received from ${deviceId}: ${type}`);
  }

  private async handleMeetingEvent(payload: {
    deviceId: string;
    event: 'joined' | 'left';
    meetingId: string;
    platform: string;
  }): Promise<void> {
    const { deviceId, event, meetingId, platform } = payload;

    await Metrics.create({
      deviceId,
      type: `meeting_${event}`,
      data: { meetingId, platform },
      timestamp: new Date(),
    });

    logger.info(`Device ${deviceId}: Meeting ${event} (${platform})`);

    // Broadcast to dashboard clients
    this.broadcast({
      type: 'meeting_update',
      payload: { deviceId, event, meetingId, platform },
    });
  }

  private async handleDisconnect(deviceId: string): Promise<void> {
    this.devices.delete(deviceId);

    await Device.update(
      { status: 'offline' },
      { where: { id: deviceId } }
    );

    logger.info(`Device ${deviceId} disconnected`);
  }

  private async checkHeartbeats(): Promise<void> {
    const timeout = 60000; // 60 seconds
    const now = Date.now();

    for (const [deviceId, connection] of this.devices) {
      if (now - connection.lastHeartbeat.getTime() > timeout) {
        logger.warn(`Device ${deviceId} heartbeat timeout`);
        connection.ws.terminate();
        this.devices.delete(deviceId);

        await Device.update(
          { status: 'offline' },
          { where: { id: deviceId } }
        );
      }
    }
  }

  // Send command to specific device
  public sendToDevice(deviceId: string, message: WSMessage): boolean {
    const connection = this.devices.get(deviceId);
    if (connection && connection.ws.readyState === WebSocket.OPEN) {
      connection.ws.send(JSON.stringify(message));
      return true;
    }
    return false;
  }

  // Broadcast to all connected devices
  public broadcast(message: WSMessage, excludeDeviceId?: string): void {
    const data = JSON.stringify(message);
    for (const [deviceId, connection] of this.devices) {
      if (deviceId !== excludeDeviceId && connection.ws.readyState === WebSocket.OPEN) {
        connection.ws.send(data);
      }
    }
  }

  // Get connected device count
  public getConnectedCount(): number {
    return this.devices.size;
  }

  // Close server
  public close(): void {
    clearInterval(this.heartbeatInterval);

    for (const connection of this.devices.values()) {
      connection.ws.terminate();
    }

    this.wss.close();
    logger.info('WebSocket server closed');
  }
}
