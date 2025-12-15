/**
 * Device management routes.
 */

import { Router, Response } from 'express';
import { Device } from '../models';
import { AuthRequest, requireRole } from '../middleware/auth';
import { logger } from '../services/logger';

export const deviceRouter = Router();

// List all devices
deviceRouter.get('/', async (req: AuthRequest, res: Response) => {
  try {
    const devices = await Device.findAll({
      order: [['roomName', 'ASC']],
    });

    res.json({
      devices: devices.map((d) => ({
        id: d.id,
        name: d.name,
        roomName: d.roomName,
        location: d.location,
        status: d.status,
        platform: d.platform,
        softwareVersion: d.softwareVersion,
        lastSeen: d.lastSeen,
        capabilities: d.capabilities,
      })),
      total: devices.length,
    });
  } catch (error) {
    logger.error('Error listing devices:', error);
    res.status(500).json({ error: 'Failed to list devices' });
  }
});

// Get device by ID
deviceRouter.get('/:id', async (req: AuthRequest, res: Response) => {
  try {
    const device = await Device.findByPk(req.params.id);

    if (!device) {
      res.status(404).json({ error: 'Device not found' });
      return;
    }

    res.json({
      id: device.id,
      name: device.name,
      roomName: device.roomName,
      location: device.location,
      status: device.status,
      platform: device.platform,
      softwareVersion: device.softwareVersion,
      lastSeen: device.lastSeen,
      capabilities: device.capabilities,
      config: device.config,
      createdAt: device.createdAt,
      updatedAt: device.updatedAt,
    });
  } catch (error) {
    logger.error('Error getting device:', error);
    res.status(500).json({ error: 'Failed to get device' });
  }
});

// Update device
deviceRouter.put('/:id', requireRole('admin', 'operator'), async (req: AuthRequest, res: Response) => {
  try {
    const device = await Device.findByPk(req.params.id);

    if (!device) {
      res.status(404).json({ error: 'Device not found' });
      return;
    }

    const { name, roomName, location, config } = req.body;

    await device.update({
      ...(name && { name }),
      ...(roomName && { roomName }),
      ...(location !== undefined && { location }),
      ...(config && { config }),
    });

    res.json({
      message: 'Device updated',
      device: {
        id: device.id,
        name: device.name,
        roomName: device.roomName,
        location: device.location,
      },
    });
  } catch (error) {
    logger.error('Error updating device:', error);
    res.status(500).json({ error: 'Failed to update device' });
  }
});

// Delete device
deviceRouter.delete('/:id', requireRole('admin'), async (req: AuthRequest, res: Response) => {
  try {
    const device = await Device.findByPk(req.params.id);

    if (!device) {
      res.status(404).json({ error: 'Device not found' });
      return;
    }

    await device.destroy();

    res.json({ message: 'Device deleted' });
  } catch (error) {
    logger.error('Error deleting device:', error);
    res.status(500).json({ error: 'Failed to delete device' });
  }
});

// Send command to device
deviceRouter.post('/:id/command', requireRole('admin', 'operator'), async (req: AuthRequest, res: Response) => {
  try {
    const device = await Device.findByPk(req.params.id);

    if (!device) {
      res.status(404).json({ error: 'Device not found' });
      return;
    }

    const { command, params } = req.body;

    if (!command) {
      res.status(400).json({ error: 'Command required' });
      return;
    }

    // TODO: Send command via WebSocket
    logger.info(`Command ${command} queued for device ${device.id}`);

    res.json({
      message: 'Command queued',
      command,
      deviceId: device.id,
    });
  } catch (error) {
    logger.error('Error sending command:', error);
    res.status(500).json({ error: 'Failed to send command' });
  }
});

// Get device status summary
deviceRouter.get('/summary/status', async (req: AuthRequest, res: Response) => {
  try {
    const devices = await Device.findAll();

    const summary = {
      total: devices.length,
      online: devices.filter((d) => d.status === 'online').length,
      offline: devices.filter((d) => d.status === 'offline').length,
      error: devices.filter((d) => d.status === 'error').length,
      provisioning: devices.filter((d) => d.status === 'provisioning').length,
    };

    res.json(summary);
  } catch (error) {
    logger.error('Error getting status summary:', error);
    res.status(500).json({ error: 'Failed to get status summary' });
  }
});
