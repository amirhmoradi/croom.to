/**
 * Database models using Sequelize.
 */

import { Sequelize, DataTypes, Model, Optional } from 'sequelize';
import { logger } from '../services/logger';

// Database connection
const sequelize = new Sequelize({
  dialect: 'postgres',
  host: process.env.DB_HOST || 'localhost',
  port: Number(process.env.DB_PORT) || 5432,
  database: process.env.DB_NAME || 'pimeet',
  username: process.env.DB_USER || 'pimeet',
  password: process.env.DB_PASSWORD || 'pimeet',
  logging: (msg) => logger.debug(msg),
});

// Device attributes
interface DeviceAttributes {
  id: string;
  name: string;
  roomName: string;
  location: string;
  status: 'online' | 'offline' | 'error' | 'provisioning';
  platform: string;
  softwareVersion: string;
  lastSeen: Date;
  capabilities: object;
  config: object;
  enrollmentToken?: string;
  createdAt?: Date;
  updatedAt?: Date;
}

interface DeviceCreationAttributes extends Optional<DeviceAttributes, 'id' | 'status' | 'lastSeen' | 'capabilities' | 'config'> {}

// Device model
export class Device extends Model<DeviceAttributes, DeviceCreationAttributes> implements DeviceAttributes {
  public id!: string;
  public name!: string;
  public roomName!: string;
  public location!: string;
  public status!: 'online' | 'offline' | 'error' | 'provisioning';
  public platform!: string;
  public softwareVersion!: string;
  public lastSeen!: Date;
  public capabilities!: object;
  public config!: object;
  public enrollmentToken?: string;
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
}

Device.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    name: {
      type: DataTypes.STRING(255),
      allowNull: false,
    },
    roomName: {
      type: DataTypes.STRING(255),
      allowNull: false,
    },
    location: {
      type: DataTypes.STRING(255),
      allowNull: true,
    },
    status: {
      type: DataTypes.ENUM('online', 'offline', 'error', 'provisioning'),
      defaultValue: 'provisioning',
    },
    platform: {
      type: DataTypes.STRING(50),
      allowNull: false,
    },
    softwareVersion: {
      type: DataTypes.STRING(50),
      allowNull: false,
    },
    lastSeen: {
      type: DataTypes.DATE,
      defaultValue: DataTypes.NOW,
    },
    capabilities: {
      type: DataTypes.JSONB,
      defaultValue: {},
    },
    config: {
      type: DataTypes.JSONB,
      defaultValue: {},
    },
    enrollmentToken: {
      type: DataTypes.STRING(255),
      allowNull: true,
    },
  },
  {
    sequelize,
    tableName: 'devices',
    timestamps: true,
  }
);

// User attributes
interface UserAttributes {
  id: string;
  email: string;
  passwordHash: string;
  name: string;
  role: 'admin' | 'operator' | 'viewer';
  createdAt?: Date;
  updatedAt?: Date;
}

interface UserCreationAttributes extends Optional<UserAttributes, 'id' | 'role'> {}

// User model
export class User extends Model<UserAttributes, UserCreationAttributes> implements UserAttributes {
  public id!: string;
  public email!: string;
  public passwordHash!: string;
  public name!: string;
  public role!: 'admin' | 'operator' | 'viewer';
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
}

User.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    email: {
      type: DataTypes.STRING(255),
      allowNull: false,
      unique: true,
    },
    passwordHash: {
      type: DataTypes.STRING(255),
      allowNull: false,
    },
    name: {
      type: DataTypes.STRING(255),
      allowNull: false,
    },
    role: {
      type: DataTypes.ENUM('admin', 'operator', 'viewer'),
      defaultValue: 'viewer',
    },
  },
  {
    sequelize,
    tableName: 'users',
    timestamps: true,
  }
);

// Metrics model
interface MetricsAttributes {
  id: string;
  deviceId: string;
  timestamp: Date;
  type: string;
  data: object;
}

interface MetricsCreationAttributes extends Optional<MetricsAttributes, 'id'> {}

export class Metrics extends Model<MetricsAttributes, MetricsCreationAttributes> implements MetricsAttributes {
  public id!: string;
  public deviceId!: string;
  public timestamp!: Date;
  public type!: string;
  public data!: object;
}

Metrics.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    deviceId: {
      type: DataTypes.UUID,
      allowNull: false,
      references: {
        model: Device,
        key: 'id',
      },
    },
    timestamp: {
      type: DataTypes.DATE,
      defaultValue: DataTypes.NOW,
    },
    type: {
      type: DataTypes.STRING(50),
      allowNull: false,
    },
    data: {
      type: DataTypes.JSONB,
      defaultValue: {},
    },
  },
  {
    sequelize,
    tableName: 'metrics',
    timestamps: false,
    indexes: [
      { fields: ['deviceId', 'timestamp'] },
      { fields: ['type', 'timestamp'] },
    ],
  }
);

// Relationships
Device.hasMany(Metrics, { foreignKey: 'deviceId' });
Metrics.belongsTo(Device, { foreignKey: 'deviceId' });

// Initialize database
export async function initDatabase(): Promise<void> {
  try {
    await sequelize.authenticate();
    logger.info('Database connection established');

    // Sync models (use migrations in production)
    if (process.env.NODE_ENV !== 'production') {
      await sequelize.sync({ alter: true });
      logger.info('Database synchronized');
    }
  } catch (error) {
    logger.error('Database initialization failed:', error);
    throw error;
  }
}

export { sequelize };
