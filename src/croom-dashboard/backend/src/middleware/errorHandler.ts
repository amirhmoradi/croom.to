/**
 * Express error handling middleware.
 */

import { Request, Response, NextFunction } from 'express';
import { logger } from '../services/logger';

export interface ApiError extends Error {
  statusCode?: number;
  code?: string;
}

export function errorHandler(
  err: ApiError,
  req: Request,
  res: Response,
  next: NextFunction
): void {
  logger.error('API Error:', {
    message: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
  });

  const statusCode = err.statusCode || 500;
  const message = statusCode === 500 ? 'Internal server error' : err.message;

  res.status(statusCode).json({
    error: message,
    code: err.code,
    ...(process.env.NODE_ENV !== 'production' && { stack: err.stack }),
  });
}
