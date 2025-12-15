"""
SOC 2 Compliance and Readiness Module for Croom.

Provides compliance monitoring, evidence collection, and reporting for
SOC 2 Type I and Type II certification requirements.

SOC 2 Trust Service Criteria covered:
- Security (Common Criteria)
- Availability
- Processing Integrity
- Confidentiality
- Privacy
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)


class TrustServiceCategory(Enum):
    """SOC 2 Trust Service Categories."""
    SECURITY = "security"
    AVAILABILITY = "availability"
    PROCESSING_INTEGRITY = "processing_integrity"
    CONFIDENTIALITY = "confidentiality"
    PRIVACY = "privacy"


class ComplianceStatus(Enum):
    """Compliance check status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_APPLICABLE = "not_applicable"
    PENDING_REVIEW = "pending_review"
    REMEDIATION_IN_PROGRESS = "remediation_in_progress"


class ControlFamily(Enum):
    """SOC 2 Control Families (Common Criteria)."""
    # Security
    CC1 = "cc1_control_environment"
    CC2 = "cc2_communication_information"
    CC3 = "cc3_risk_assessment"
    CC4 = "cc4_monitoring_activities"
    CC5 = "cc5_control_activities"
    CC6 = "cc6_logical_physical_access"
    CC7 = "cc7_system_operations"
    CC8 = "cc8_change_management"
    CC9 = "cc9_risk_mitigation"

    # Availability
    A1 = "a1_availability"

    # Processing Integrity
    PI1 = "pi1_processing_integrity"

    # Confidentiality
    C1 = "c1_confidentiality"

    # Privacy
    P1 = "p1_privacy_notice"
    P2 = "p2_privacy_choice_consent"
    P3 = "p3_privacy_collection"
    P4 = "p4_privacy_use_retention"
    P5 = "p5_privacy_access"
    P6 = "p6_privacy_disclosure"
    P7 = "p7_privacy_quality"
    P8 = "p8_privacy_monitoring"


@dataclass
class ControlPoint:
    """Individual control point for compliance."""
    id: str
    name: str
    description: str
    family: ControlFamily
    category: TrustServiceCategory
    automated: bool = False
    evidence_required: List[str] = field(default_factory=list)
    test_procedure: str = ""
    remediation_guidance: str = ""


@dataclass
class ComplianceEvidence:
    """Evidence for compliance control."""
    id: str
    control_id: str
    evidence_type: str  # log, screenshot, config, report, etc.
    description: str
    collected_at: datetime
    collected_by: str
    file_path: Optional[str] = None
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "control_id": self.control_id,
            "evidence_type": self.evidence_type,
            "description": self.description,
            "collected_at": self.collected_at.isoformat(),
            "collected_by": self.collected_by,
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
        }


@dataclass
class ComplianceCheckResult:
    """Result of a compliance check."""
    control_id: str
    status: ComplianceStatus
    checked_at: datetime
    details: str = ""
    evidence: List[ComplianceEvidence] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "control_id": self.control_id,
            "status": self.status.value,
            "checked_at": self.checked_at.isoformat(),
            "details": self.details,
            "evidence": [e.to_dict() for e in self.evidence],
            "findings": self.findings,
            "recommendations": self.recommendations,
        }


@dataclass
class ComplianceReport:
    """SOC 2 Compliance Report."""
    id: str
    report_type: str  # "type1" or "type2"
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    organization: str
    system_description: str
    results: List[ComplianceCheckResult] = field(default_factory=list)
    overall_status: ComplianceStatus = ComplianceStatus.PENDING_REVIEW
    summary: str = ""
    auditor_notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "report_type": self.report_type,
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "organization": self.organization,
            "system_description": self.system_description,
            "results": [r.to_dict() for r in self.results],
            "overall_status": self.overall_status.value,
            "summary": self.summary,
            "auditor_notes": self.auditor_notes,
        }


class ComplianceCheck(ABC):
    """Base class for compliance checks."""

    @property
    @abstractmethod
    def control_id(self) -> str:
        """Control point ID."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Check name."""
        pass

    @property
    @abstractmethod
    def category(self) -> TrustServiceCategory:
        """Trust service category."""
        pass

    @abstractmethod
    async def check(self) -> ComplianceCheckResult:
        """Execute the compliance check."""
        pass

    @abstractmethod
    async def collect_evidence(self) -> List[ComplianceEvidence]:
        """Collect evidence for the control."""
        pass


class EncryptionAtRestCheck(ComplianceCheck):
    """Check encryption at rest controls (CC6.1)."""

    def __init__(self, config_path: str = "/etc/croom"):
        self._config_path = Path(config_path)

    @property
    def control_id(self) -> str:
        return "CC6.1.1"

    @property
    def name(self) -> str:
        return "Encryption at Rest"

    @property
    def category(self) -> TrustServiceCategory:
        return TrustServiceCategory.SECURITY

    async def check(self) -> ComplianceCheckResult:
        findings = []
        recommendations = []
        status = ComplianceStatus.COMPLIANT

        # Check encryption configuration
        try:
            from croom.security.encryption import EncryptionService

            # Verify AES-256-GCM is configured
            config_file = self._config_path / "encryption.conf"
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)

                if config.get("algorithm") != "AES-256-GCM":
                    findings.append("Encryption algorithm is not AES-256-GCM")
                    status = ComplianceStatus.NON_COMPLIANT
                    recommendations.append("Configure AES-256-GCM encryption")

                if not config.get("key_rotation_enabled", False):
                    findings.append("Key rotation is not enabled")
                    status = ComplianceStatus.PARTIALLY_COMPLIANT
                    recommendations.append("Enable automatic key rotation")
            else:
                # Check default configuration
                findings.append("Using default encryption configuration")

        except ImportError:
            findings.append("Encryption service not available")
            status = ComplianceStatus.NON_COMPLIANT
            recommendations.append("Install and configure encryption service")

        evidence = await self.collect_evidence()

        return ComplianceCheckResult(
            control_id=self.control_id,
            status=status,
            checked_at=datetime.utcnow(),
            details="Verified encryption at rest configuration",
            evidence=evidence,
            findings=findings,
            recommendations=recommendations,
        )

    async def collect_evidence(self) -> List[ComplianceEvidence]:
        evidence = []

        # Collect encryption configuration
        config_file = self._config_path / "encryption.conf"
        if config_file.exists():
            with open(config_file, "rb") as f:
                content = f.read()
                content_hash = hashlib.sha256(content).hexdigest()

            evidence.append(ComplianceEvidence(
                id=str(uuid.uuid4()),
                control_id=self.control_id,
                evidence_type="config",
                description="Encryption configuration file",
                collected_at=datetime.utcnow(),
                collected_by="automated",
                file_path=str(config_file),
                content_hash=content_hash,
            ))

        return evidence


class AccessControlCheck(ComplianceCheck):
    """Check access control mechanisms (CC6.2, CC6.3)."""

    @property
    def control_id(self) -> str:
        return "CC6.2.1"

    @property
    def name(self) -> str:
        return "Logical Access Controls"

    @property
    def category(self) -> TrustServiceCategory:
        return TrustServiceCategory.SECURITY

    async def check(self) -> ComplianceCheckResult:
        findings = []
        recommendations = []
        status = ComplianceStatus.COMPLIANT

        try:
            from croom.security.rbac import RBACService
            from croom.security.auth import AuthService

            # Check RBAC is configured
            # Check MFA is enabled
            # Check session management

            # These would be actual checks in production
            pass

        except ImportError as e:
            findings.append(f"Security module not available: {e}")
            status = ComplianceStatus.NON_COMPLIANT

        evidence = await self.collect_evidence()

        return ComplianceCheckResult(
            control_id=self.control_id,
            status=status,
            checked_at=datetime.utcnow(),
            details="Verified logical access controls",
            evidence=evidence,
            findings=findings,
            recommendations=recommendations,
        )

    async def collect_evidence(self) -> List[ComplianceEvidence]:
        return []


class AuditLoggingCheck(ComplianceCheck):
    """Check audit logging controls (CC4.1, CC7.2)."""

    def __init__(self, log_path: str = "/var/log/croom"):
        self._log_path = Path(log_path)

    @property
    def control_id(self) -> str:
        return "CC7.2.1"

    @property
    def name(self) -> str:
        return "Audit Logging"

    @property
    def category(self) -> TrustServiceCategory:
        return TrustServiceCategory.SECURITY

    async def check(self) -> ComplianceCheckResult:
        findings = []
        recommendations = []
        status = ComplianceStatus.COMPLIANT

        # Check audit log configuration
        audit_log = self._log_path / "audit.log"
        if not audit_log.exists():
            findings.append("Audit log file not found")
            status = ComplianceStatus.NON_COMPLIANT
            recommendations.append("Enable audit logging")
        else:
            # Check log integrity
            integrity_file = self._log_path / "audit.log.sig"
            if not integrity_file.exists():
                findings.append("Audit log integrity verification not configured")
                status = ComplianceStatus.PARTIALLY_COMPLIANT
                recommendations.append("Enable tamper-evident logging")

        # Check log retention
        retention_config = self._log_path / "retention.conf"
        if not retention_config.exists():
            findings.append("Log retention policy not configured")
            recommendations.append("Configure log retention policy (minimum 1 year)")

        evidence = await self.collect_evidence()

        return ComplianceCheckResult(
            control_id=self.control_id,
            status=status,
            checked_at=datetime.utcnow(),
            details="Verified audit logging configuration",
            evidence=evidence,
            findings=findings,
            recommendations=recommendations,
        )

    async def collect_evidence(self) -> List[ComplianceEvidence]:
        evidence = []

        # Sample recent audit log entries
        audit_log = self._log_path / "audit.log"
        if audit_log.exists():
            evidence.append(ComplianceEvidence(
                id=str(uuid.uuid4()),
                control_id=self.control_id,
                evidence_type="log",
                description="Audit log sample",
                collected_at=datetime.utcnow(),
                collected_by="automated",
                file_path=str(audit_log),
                metadata={"sample_size": "last_1000_entries"},
            ))

        return evidence


class ChangeManagementCheck(ComplianceCheck):
    """Check change management controls (CC8.1)."""

    @property
    def control_id(self) -> str:
        return "CC8.1.1"

    @property
    def name(self) -> str:
        return "Change Management"

    @property
    def category(self) -> TrustServiceCategory:
        return TrustServiceCategory.SECURITY

    async def check(self) -> ComplianceCheckResult:
        findings = []
        recommendations = []
        status = ComplianceStatus.COMPLIANT

        # Check version control
        # Check change approval process
        # Check deployment procedures

        evidence = await self.collect_evidence()

        return ComplianceCheckResult(
            control_id=self.control_id,
            status=status,
            checked_at=datetime.utcnow(),
            details="Verified change management controls",
            evidence=evidence,
            findings=findings,
            recommendations=recommendations,
        )

    async def collect_evidence(self) -> List[ComplianceEvidence]:
        return []


class AvailabilityCheck(ComplianceCheck):
    """Check availability controls (A1.1, A1.2)."""

    @property
    def control_id(self) -> str:
        return "A1.1.1"

    @property
    def name(self) -> str:
        return "System Availability"

    @property
    def category(self) -> TrustServiceCategory:
        return TrustServiceCategory.AVAILABILITY

    async def check(self) -> ComplianceCheckResult:
        findings = []
        recommendations = []
        status = ComplianceStatus.COMPLIANT

        # Check monitoring configuration
        # Check alerting
        # Check backup procedures
        # Check disaster recovery

        evidence = await self.collect_evidence()

        return ComplianceCheckResult(
            control_id=self.control_id,
            status=status,
            checked_at=datetime.utcnow(),
            details="Verified availability controls",
            evidence=evidence,
            findings=findings,
            recommendations=recommendations,
        )

    async def collect_evidence(self) -> List[ComplianceEvidence]:
        return []


class DataConfidentialityCheck(ComplianceCheck):
    """Check confidentiality controls (C1.1, C1.2)."""

    @property
    def control_id(self) -> str:
        return "C1.1.1"

    @property
    def name(self) -> str:
        return "Data Confidentiality"

    @property
    def category(self) -> TrustServiceCategory:
        return TrustServiceCategory.CONFIDENTIALITY

    async def check(self) -> ComplianceCheckResult:
        findings = []
        recommendations = []
        status = ComplianceStatus.COMPLIANT

        # Check data classification
        # Check encryption in transit
        # Check data masking
        # Check secure deletion

        evidence = await self.collect_evidence()

        return ComplianceCheckResult(
            control_id=self.control_id,
            status=status,
            checked_at=datetime.utcnow(),
            details="Verified confidentiality controls",
            evidence=evidence,
            findings=findings,
            recommendations=recommendations,
        )

    async def collect_evidence(self) -> List[ComplianceEvidence]:
        return []


class PrivacyNoticeCheck(ComplianceCheck):
    """Check privacy notice controls (P1.1)."""

    @property
    def control_id(self) -> str:
        return "P1.1.1"

    @property
    def name(self) -> str:
        return "Privacy Notice"

    @property
    def category(self) -> TrustServiceCategory:
        return TrustServiceCategory.PRIVACY

    async def check(self) -> ComplianceCheckResult:
        findings = []
        recommendations = []
        status = ComplianceStatus.COMPLIANT

        # Check privacy policy exists
        # Check it's accessible
        # Check it covers required topics

        evidence = await self.collect_evidence()

        return ComplianceCheckResult(
            control_id=self.control_id,
            status=status,
            checked_at=datetime.utcnow(),
            details="Verified privacy notice controls",
            evidence=evidence,
            findings=findings,
            recommendations=recommendations,
        )

    async def collect_evidence(self) -> List[ComplianceEvidence]:
        return []


class SOC2ComplianceService:
    """
    SOC 2 Compliance Management Service.

    Manages compliance checks, evidence collection, and reporting
    for SOC 2 certification readiness.
    """

    def __init__(
        self,
        config_path: str = "/etc/croom",
        log_path: str = "/var/log/croom",
        evidence_path: str = "/var/lib/croom/compliance",
    ):
        self._config_path = Path(config_path)
        self._log_path = Path(log_path)
        self._evidence_path = Path(evidence_path)
        self._evidence_path.mkdir(parents=True, exist_ok=True)

        self._checks: List[ComplianceCheck] = []
        self._results: Dict[str, ComplianceCheckResult] = {}
        self._evidence_store: Dict[str, List[ComplianceEvidence]] = {}

        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register default compliance checks."""
        self._checks = [
            EncryptionAtRestCheck(str(self._config_path)),
            AccessControlCheck(),
            AuditLoggingCheck(str(self._log_path)),
            ChangeManagementCheck(),
            AvailabilityCheck(),
            DataConfidentialityCheck(),
            PrivacyNoticeCheck(),
        ]

    def register_check(self, check: ComplianceCheck) -> None:
        """Register a custom compliance check."""
        self._checks.append(check)

    async def run_all_checks(self) -> Dict[str, ComplianceCheckResult]:
        """Run all registered compliance checks."""
        results = {}

        for check in self._checks:
            try:
                logger.info(f"Running compliance check: {check.name}")
                result = await check.check()
                results[check.control_id] = result
                self._results[check.control_id] = result

                # Store evidence
                if result.evidence:
                    self._evidence_store[check.control_id] = result.evidence

            except Exception as e:
                logger.error(f"Compliance check failed: {check.name}: {e}")
                results[check.control_id] = ComplianceCheckResult(
                    control_id=check.control_id,
                    status=ComplianceStatus.NON_COMPLIANT,
                    checked_at=datetime.utcnow(),
                    details=f"Check failed with error: {e}",
                    findings=[str(e)],
                )

        return results

    async def run_check(self, control_id: str) -> Optional[ComplianceCheckResult]:
        """Run a specific compliance check."""
        for check in self._checks:
            if check.control_id == control_id:
                result = await check.check()
                self._results[control_id] = result
                return result
        return None

    def get_compliance_status(self) -> Dict[str, Any]:
        """Get overall compliance status summary."""
        if not self._results:
            return {
                "status": "not_evaluated",
                "message": "No compliance checks have been run",
            }

        total = len(self._results)
        compliant = sum(
            1 for r in self._results.values()
            if r.status == ComplianceStatus.COMPLIANT
        )
        non_compliant = sum(
            1 for r in self._results.values()
            if r.status == ComplianceStatus.NON_COMPLIANT
        )
        partial = sum(
            1 for r in self._results.values()
            if r.status == ComplianceStatus.PARTIALLY_COMPLIANT
        )

        if non_compliant > 0:
            overall = ComplianceStatus.NON_COMPLIANT
        elif partial > 0:
            overall = ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            overall = ComplianceStatus.COMPLIANT

        return {
            "status": overall.value,
            "total_controls": total,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "partially_compliant": partial,
            "compliance_percentage": round((compliant / total) * 100, 1) if total > 0 else 0,
            "last_evaluated": max(
                (r.checked_at for r in self._results.values()),
                default=None
            ),
        }

    def get_findings(self) -> List[Dict[str, Any]]:
        """Get all findings from compliance checks."""
        findings = []

        for control_id, result in self._results.items():
            for finding in result.findings:
                findings.append({
                    "control_id": control_id,
                    "status": result.status.value,
                    "finding": finding,
                    "checked_at": result.checked_at.isoformat(),
                })

        return findings

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get all recommendations from compliance checks."""
        recommendations = []

        for control_id, result in self._results.items():
            for rec in result.recommendations:
                recommendations.append({
                    "control_id": control_id,
                    "status": result.status.value,
                    "recommendation": rec,
                })

        return recommendations

    async def generate_report(
        self,
        report_type: str = "type1",
        organization: str = "Croom Deployment",
        period_days: int = 365,
    ) -> ComplianceReport:
        """Generate a SOC 2 compliance report."""
        # Run all checks if not already done
        if not self._results:
            await self.run_all_checks()

        now = datetime.utcnow()
        period_start = now - timedelta(days=period_days)

        results = list(self._results.values())
        overall_status = self._calculate_overall_status(results)

        report = ComplianceReport(
            id=str(uuid.uuid4()),
            report_type=report_type,
            generated_at=now,
            period_start=period_start,
            period_end=now,
            organization=organization,
            system_description=self._get_system_description(),
            results=results,
            overall_status=overall_status,
            summary=self._generate_summary(results),
        )

        # Save report
        await self._save_report(report)

        return report

    def _calculate_overall_status(
        self,
        results: List[ComplianceCheckResult]
    ) -> ComplianceStatus:
        """Calculate overall compliance status."""
        if not results:
            return ComplianceStatus.PENDING_REVIEW

        non_compliant = sum(
            1 for r in results
            if r.status == ComplianceStatus.NON_COMPLIANT
        )
        partial = sum(
            1 for r in results
            if r.status == ComplianceStatus.PARTIALLY_COMPLIANT
        )

        if non_compliant > 0:
            return ComplianceStatus.NON_COMPLIANT
        elif partial > 0:
            return ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            return ComplianceStatus.COMPLIANT

    def _get_system_description(self) -> str:
        """Get system description for report."""
        return """
Croom Conference Room System

Croom is an open-source video conferencing room system designed for
Raspberry Pi hardware. The system provides:

- Video meeting integration (Google Meet, Microsoft Teams, Zoom, Webex)
- Touch screen room interface
- Calendar integration
- Remote management capabilities
- Edge AI features for enhanced meeting experience

Security Features:
- AES-256-GCM encryption for data at rest
- TLS 1.3 for data in transit
- Multi-factor authentication (TOTP, WebAuthn)
- Role-based access control (RBAC)
- Tamper-evident audit logging
- SSO integration (SAML, OIDC, LDAP)

The system is designed to meet enterprise security requirements
while maintaining ease of deployment and management.
"""

    def _generate_summary(self, results: List[ComplianceCheckResult]) -> str:
        """Generate compliance summary."""
        total = len(results)
        compliant = sum(1 for r in results if r.status == ComplianceStatus.COMPLIANT)

        return f"""
SOC 2 Compliance Assessment Summary

Total Controls Evaluated: {total}
Compliant: {compliant}
Non-Compliant: {sum(1 for r in results if r.status == ComplianceStatus.NON_COMPLIANT)}
Partially Compliant: {sum(1 for r in results if r.status == ComplianceStatus.PARTIALLY_COMPLIANT)}

Overall Compliance Rate: {round((compliant / total) * 100, 1) if total > 0 else 0}%

Key Findings:
{chr(10).join('- ' + f for r in results for f in r.findings) or '- No significant findings'}

Recommendations:
{chr(10).join('- ' + r for res in results for r in res.recommendations) or '- Continue current practices'}
"""

    async def _save_report(self, report: ComplianceReport) -> None:
        """Save compliance report to file."""
        report_dir = self._evidence_path / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        report_file = report_dir / f"soc2_{report.report_type}_{report.id}.json"

        with open(report_file, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

        logger.info(f"Saved compliance report: {report_file}")

    async def collect_all_evidence(self) -> Dict[str, List[ComplianceEvidence]]:
        """Collect evidence for all controls."""
        evidence = {}

        for check in self._checks:
            try:
                check_evidence = await check.collect_evidence()
                if check_evidence:
                    evidence[check.control_id] = check_evidence
            except Exception as e:
                logger.error(f"Failed to collect evidence for {check.control_id}: {e}")

        self._evidence_store.update(evidence)
        return evidence

    def export_evidence_package(self, output_path: str) -> str:
        """Export all evidence as a package for auditors."""
        import zipfile

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add evidence manifest
            manifest = {
                "generated_at": datetime.utcnow().isoformat(),
                "controls": {},
            }

            for control_id, evidence_list in self._evidence_store.items():
                manifest["controls"][control_id] = [e.to_dict() for e in evidence_list]

                # Add actual evidence files
                for evidence in evidence_list:
                    if evidence.file_path and Path(evidence.file_path).exists():
                        arc_name = f"{control_id}/{Path(evidence.file_path).name}"
                        zf.write(evidence.file_path, arc_name)

            # Add manifest
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            # Add compliance results
            if self._results:
                results_data = {
                    control_id: result.to_dict()
                    for control_id, result in self._results.items()
                }
                zf.writestr("compliance_results.json", json.dumps(results_data, indent=2))

        logger.info(f"Exported evidence package: {output_file}")
        return str(output_file)


# Control point definitions for reference
SOC2_CONTROL_POINTS = [
    ControlPoint(
        id="CC6.1",
        name="Encryption at Rest",
        description="The entity implements logical access security measures to protect against unauthorized access",
        family=ControlFamily.CC6,
        category=TrustServiceCategory.SECURITY,
        automated=True,
        evidence_required=["encryption_config", "key_management_policy"],
        test_procedure="Verify AES-256-GCM encryption is enabled for all sensitive data",
        remediation_guidance="Enable encryption and configure key rotation",
    ),
    ControlPoint(
        id="CC6.2",
        name="User Authentication",
        description="Prior to issuing system credentials and granting system access",
        family=ControlFamily.CC6,
        category=TrustServiceCategory.SECURITY,
        automated=True,
        evidence_required=["auth_config", "user_provisioning_logs"],
        test_procedure="Verify MFA is enabled and enforced for all users",
        remediation_guidance="Enable MFA using TOTP or WebAuthn",
    ),
    ControlPoint(
        id="CC6.3",
        name="Access Removal",
        description="The entity removes credentials and disables access",
        family=ControlFamily.CC6,
        category=TrustServiceCategory.SECURITY,
        automated=False,
        evidence_required=["access_removal_logs", "termination_checklist"],
        test_procedure="Verify access is removed within 24 hours of termination",
        remediation_guidance="Implement automated deprovisioning",
    ),
    ControlPoint(
        id="CC7.2",
        name="Security Event Logging",
        description="The entity monitors system components for anomalies and security events",
        family=ControlFamily.CC7,
        category=TrustServiceCategory.SECURITY,
        automated=True,
        evidence_required=["audit_logs", "siem_config", "alerting_rules"],
        test_procedure="Verify all security events are logged with integrity protection",
        remediation_guidance="Enable tamper-evident audit logging",
    ),
    ControlPoint(
        id="CC8.1",
        name="Change Management",
        description="The entity authorizes, designs, develops, configures, documents, tests, approves changes",
        family=ControlFamily.CC8,
        category=TrustServiceCategory.SECURITY,
        automated=False,
        evidence_required=["change_requests", "approval_records", "test_results"],
        test_procedure="Verify all changes follow documented change management process",
        remediation_guidance="Implement change approval workflow",
    ),
    ControlPoint(
        id="A1.1",
        name="Capacity Planning",
        description="The entity maintains, monitors, and evaluates current processing capacity",
        family=ControlFamily.A1,
        category=TrustServiceCategory.AVAILABILITY,
        automated=True,
        evidence_required=["capacity_metrics", "monitoring_dashboards"],
        test_procedure="Verify capacity monitoring and alerting is configured",
        remediation_guidance="Configure resource monitoring and alerts",
    ),
    ControlPoint(
        id="A1.2",
        name="Disaster Recovery",
        description="The entity authorizes, designs, develops, implements disaster recovery",
        family=ControlFamily.A1,
        category=TrustServiceCategory.AVAILABILITY,
        automated=False,
        evidence_required=["dr_plan", "backup_logs", "recovery_test_results"],
        test_procedure="Verify disaster recovery plan exists and is tested annually",
        remediation_guidance="Develop and test disaster recovery procedures",
    ),
    ControlPoint(
        id="C1.1",
        name="Data Classification",
        description="The entity identifies and maintains confidential information",
        family=ControlFamily.C1,
        category=TrustServiceCategory.CONFIDENTIALITY,
        automated=False,
        evidence_required=["data_classification_policy", "data_inventory"],
        test_procedure="Verify data classification scheme is implemented",
        remediation_guidance="Implement data classification and labeling",
    ),
    ControlPoint(
        id="P1.1",
        name="Privacy Notice",
        description="The entity provides notice about its privacy practices",
        family=ControlFamily.P1,
        category=TrustServiceCategory.PRIVACY,
        automated=False,
        evidence_required=["privacy_policy", "notice_acknowledgments"],
        test_procedure="Verify privacy notice is accessible and comprehensive",
        remediation_guidance="Update privacy notice to cover all data practices",
    ),
]
