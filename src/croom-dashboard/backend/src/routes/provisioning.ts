/**
 * Device provisioning routes.
 *
 * Zero-touch provisioning flow:
 * 1. Admin creates enrollment token in dashboard
 * 2. Device boots with token (from QR code or config)
 * 3. Device calls /api/provisioning/enroll with token
 * 4. Dashboard validates token, creates device record
 * 5. Device receives config and connects via WebSocket
 */

import { Router, Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { Device } from '../models';
import { authMiddleware, AuthRequest, requireRole } from '../middleware/auth';
import { logger } from '../services/logger';

export const provisioningRouter = Router();

// Generate enrollment token (admin only)
provisioningRouter.post(
  '/token',
  authMiddleware,
  requireRole('admin'),
  async (req: AuthRequest, res: Response) => {
    try {
      const { roomName, location, expiresInHours = 24 } = req.body;

      if (!roomName) {
        res.status(400).json({ error: 'Room name required' });
        return;
      }

      const token = uuidv4();
      const expiresAt = new Date(Date.now() + expiresInHours * 60 * 60 * 1000);

      // Create pending device record
      const device = await Device.create({
        name: `device-${token.slice(0, 8)}`,
        roomName,
        location: location || '',
        status: 'provisioning',
        platform: 'unknown',
        softwareVersion: 'unknown',
        enrollmentToken: token,
      });

      logger.info(`Enrollment token created for room ${roomName}`);

      res.status(201).json({
        token,
        deviceId: device.id,
        roomName,
        expiresAt: expiresAt.toISOString(),
        enrollmentUrl: `${process.env.BASE_URL || 'http://localhost:3001'}/api/provisioning/enroll`,
      });
    } catch (error) {
      logger.error('Error creating enrollment token:', error);
      res.status(500).json({ error: 'Failed to create token' });
    }
  }
);

// Device enrollment (called by device during setup)
provisioningRouter.post('/enroll', async (req: Request, res: Response) => {
  try {
    const { token, deviceInfo } = req.body;

    if (!token) {
      res.status(400).json({ error: 'Enrollment token required' });
      return;
    }

    // Find device with token
    const device = await Device.findOne({
      where: { enrollmentToken: token },
    });

    if (!device) {
      res.status(401).json({ error: 'Invalid enrollment token' });
      return;
    }

    if (device.status !== 'provisioning') {
      res.status(409).json({ error: 'Device already enrolled' });
      return;
    }

    // Update device info
    const {
      platform = 'rpi5',
      softwareVersion = '2.0.0',
      capabilities = {},
      name,
    } = deviceInfo || {};

    await device.update({
      name: name || device.name,
      platform,
      softwareVersion,
      capabilities,
      status: 'online',
      enrollmentToken: null, // Clear token after use
      lastSeen: new Date(),
    });

    logger.info(`Device ${device.id} enrolled successfully`);

    // Return device config
    res.json({
      deviceId: device.id,
      config: device.config,
      websocketUrl: `${process.env.WS_URL || 'ws://localhost:3001'}/ws`,
      message: 'Device enrolled successfully',
    });
  } catch (error) {
    logger.error('Error enrolling device:', error);
    res.status(500).json({ error: 'Enrollment failed' });
  }
});

// Get pending enrollments (admin only)
provisioningRouter.get(
  '/pending',
  authMiddleware,
  requireRole('admin'),
  async (req: AuthRequest, res: Response) => {
    try {
      const devices = await Device.findAll({
        where: { status: 'provisioning' },
        order: [['createdAt', 'DESC']],
      });

      res.json({
        pendingDevices: devices.map((d) => ({
          id: d.id,
          roomName: d.roomName,
          location: d.location,
          createdAt: d.createdAt,
          hasToken: !!d.enrollmentToken,
        })),
      });
    } catch (error) {
      logger.error('Error getting pending enrollments:', error);
      res.status(500).json({ error: 'Failed to get pending enrollments' });
    }
  }
);

// Cancel enrollment (admin only)
provisioningRouter.delete(
  '/token/:deviceId',
  authMiddleware,
  requireRole('admin'),
  async (req: AuthRequest, res: Response) => {
    try {
      const device = await Device.findByPk(req.params.deviceId);

      if (!device) {
        res.status(404).json({ error: 'Device not found' });
        return;
      }

      if (device.status !== 'provisioning') {
        res.status(400).json({ error: 'Device already enrolled' });
        return;
      }

      await device.destroy();

      logger.info(`Enrollment cancelled for device ${req.params.deviceId}`);

      res.json({ message: 'Enrollment cancelled' });
    } catch (error) {
      logger.error('Error cancelling enrollment:', error);
      res.status(500).json({ error: 'Failed to cancel enrollment' });
    }
  }
);
