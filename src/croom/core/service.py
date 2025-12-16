"""
Service management for Croom.

Handles lifecycle and coordination of all Croom services.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Type, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service lifecycle states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServiceStatus:
    """Status information for a service."""
    name: str
    state: ServiceState
    message: str = ""
    error: Optional[str] = None
    uptime_seconds: float = 0


class Service(ABC):
    """Abstract base class for all Croom services."""

    def __init__(self, name: str):
        self.name = name
        self._state = ServiceState.STOPPED
        self._error: Optional[str] = None
        self._start_time: Optional[float] = None

    @property
    def state(self) -> ServiceState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state == ServiceState.RUNNING

    @abstractmethod
    async def start(self) -> None:
        """Start the service."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the service."""
        pass

    async def restart(self) -> None:
        """Restart the service."""
        await self.stop()
        await self.start()

    def get_status(self) -> ServiceStatus:
        """Get current service status."""
        import time
        uptime = 0.0
        if self._start_time and self._state == ServiceState.RUNNING:
            uptime = time.time() - self._start_time

        return ServiceStatus(
            name=self.name,
            state=self._state,
            message=f"Service {self.name} is {self._state.value}",
            error=self._error,
            uptime_seconds=uptime
        )

    def _set_state(self, state: ServiceState, error: Optional[str] = None):
        """Update service state."""
        import time
        self._state = state
        self._error = error
        if state == ServiceState.RUNNING:
            self._start_time = time.time()
        elif state == ServiceState.STOPPED:
            self._start_time = None


class ServiceManager:
    """
    Manages all Croom services.

    Handles service registration, lifecycle management, and coordination.
    """

    def __init__(self):
        self._services: Dict[str, Service] = {}
        self._start_order: List[str] = []
        self._running = False
        self._shutdown_event = asyncio.Event()

    def register(self, service: Service, dependencies: Optional[List[str]] = None) -> None:
        """
        Register a service with the manager.

        Args:
            service: Service instance to register.
            dependencies: List of service names this service depends on.
        """
        if service.name in self._services:
            raise ValueError(f"Service '{service.name}' already registered")

        self._services[service.name] = service

        # Update start order based on dependencies
        if dependencies:
            # Ensure dependencies are registered
            for dep in dependencies:
                if dep not in self._services and dep not in self._start_order:
                    logger.warning(f"Dependency '{dep}' not yet registered for '{service.name}'")

            # Add service after its dependencies
            max_idx = -1
            for dep in dependencies:
                if dep in self._start_order:
                    max_idx = max(max_idx, self._start_order.index(dep))
            self._start_order.insert(max_idx + 1, service.name)
        else:
            self._start_order.append(service.name)

        logger.info(f"Registered service: {service.name}")

    def unregister(self, name: str) -> None:
        """Unregister a service."""
        if name in self._services:
            del self._services[name]
            if name in self._start_order:
                self._start_order.remove(name)
            logger.info(f"Unregistered service: {name}")

    def get_service(self, name: str) -> Optional[Service]:
        """Get a registered service by name."""
        return self._services.get(name)

    def get_all_services(self) -> Dict[str, Service]:
        """Get all registered services."""
        return self._services.copy()

    async def start_all(self) -> bool:
        """
        Start all registered services in order.

        Returns:
            True if all services started successfully.
        """
        logger.info("Starting all services...")
        self._running = True
        self._shutdown_event.clear()

        for name in self._start_order:
            service = self._services.get(name)
            if not service:
                continue

            try:
                logger.info(f"Starting service: {name}")
                service._set_state(ServiceState.STARTING)
                await service.start()
                service._set_state(ServiceState.RUNNING)
                logger.info(f"Service started: {name}")
            except Exception as e:
                logger.error(f"Failed to start service '{name}': {e}")
                service._set_state(ServiceState.ERROR, str(e))
                # Stop already started services
                await self.stop_all()
                return False

        logger.info("All services started successfully")
        return True

    async def stop_all(self) -> None:
        """Stop all registered services in reverse order."""
        logger.info("Stopping all services...")
        self._running = False
        self._shutdown_event.set()

        # Stop in reverse order
        for name in reversed(self._start_order):
            service = self._services.get(name)
            if not service or service.state == ServiceState.STOPPED:
                continue

            try:
                logger.info(f"Stopping service: {name}")
                service._set_state(ServiceState.STOPPING)
                await service.stop()
                service._set_state(ServiceState.STOPPED)
                logger.info(f"Service stopped: {name}")
            except Exception as e:
                logger.error(f"Error stopping service '{name}': {e}")
                service._set_state(ServiceState.ERROR, str(e))

        logger.info("All services stopped")

    async def restart_service(self, name: str) -> bool:
        """
        Restart a specific service.

        Args:
            name: Name of service to restart.

        Returns:
            True if restart was successful.
        """
        service = self._services.get(name)
        if not service:
            logger.error(f"Service not found: {name}")
            return False

        try:
            logger.info(f"Restarting service: {name}")
            await service.restart()
            return True
        except Exception as e:
            logger.error(f"Failed to restart service '{name}': {e}")
            service._set_state(ServiceState.ERROR, str(e))
            return False

    def get_status(self) -> Dict[str, ServiceStatus]:
        """Get status of all services."""
        return {name: svc.get_status() for name, svc in self._services.items()}

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown_event.set()

    @property
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running
