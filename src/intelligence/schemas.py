from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class ActionItem(BaseModel):
    task: str = Field(..., description="Action item description")
    owner: Optional[str] = Field(None, description="Person responsible for the action item")
    raw_date_mention: Optional[str] = Field(None, description="Relative or raw date mention in conversation (e.g. 'Friday', '15th of next month')")
    resolved_due_date: Optional[str] = Field(None, description="Calculated due date in YYYY-MM-DD format based on call date context")
    line_numbers: List[int] = Field(..., description="Exact line numbers in the transcript this action item is based on")
    source_excerpt: str = Field(..., description="Exact verbatim excerpt from the transcript line(s)")

class Decision(BaseModel):
    decision: str = Field(..., description="Decision actually made during the call")
    line_numbers: List[int] = Field(..., description="Exact line numbers in transcript")
    source_excerpt: str = Field(..., description="Exact verbatim excerpt from the transcript line(s)")

class Blocker(BaseModel):
    blocker: str = Field(..., description="Blocker or issue stopping progress")
    line_numbers: List[int] = Field(..., description="Exact line numbers in transcript")
    source_excerpt: str = Field(..., description="Exact verbatim excerpt from the transcript line(s)")

class ComplianceObservation(BaseModel):
    category: str = Field(..., description="Category: e.g. 'Consent', 'Cease & Desist', 'Legal Mention', 'Policy Approval', 'General'")
    severity: Literal["Red", "Yellow", "Green"] = Field(..., description="Red = critical risk/policy breach, Yellow = warning/caution, Green = fully compliant")
    observation: str = Field(..., description="Detailed compliance or coaching observation")
    line_numbers: List[int] = Field(..., description="Exact line numbers in transcript")
    source_excerpt: str = Field(..., description="Exact verbatim excerpt from the transcript line(s)")

class HumanReviewItem(BaseModel):
    reason: str = Field(..., description="Reason for escalation: e.g. 'Missing Owner', 'Vague Deadline', 'Cease & Desist Trigger', 'Legal Threat', 'Supervisor Approval Required', 'Recording Consent Unclear'")
    description: str = Field(..., description="Description of what needs human judgment or review")
    line_numbers: List[int] = Field(..., description="Exact line numbers in transcript")
    source_excerpt: str = Field(..., description="Exact verbatim excerpt from the transcript line(s)")

class CallSentiment(BaseModel):
    overall_sentiment: Literal["Positive", "Neutral", "Negative"] = Field(..., description="Overall tone of the conversation")
    customer_angry: bool = Field(False, description="True if customer expressed frustration, anger, or hostility")
    profanity_detected: bool = Field(False, description="True if offensive language or profanity was used")
    sentiment_explanation: str = Field(..., description="Brief explanation of customer sentiment")

class CallIntelligenceOutput(BaseModel):
    short_tag: str = Field(..., description="Short topic tag for the call (e.g. 'Debt Collection Settlement Request')")
    summary: str = Field(..., description="Plain-language summary of the call")
    decisions: List[Decision] = Field(default_factory=list, description="Decisions made during the call")
    action_items: List[ActionItem] = Field(default_factory=list, description="Action items agreed upon")
    blockers: List[Blocker] = Field(default_factory=list, description="Blockers stopping progress")
    compliance_observations: List[ComplianceObservation] = Field(default_factory=list, description="Compliance & coaching observations")
    human_review_items: List[HumanReviewItem] = Field(default_factory=list, description="Items needing human review")
    sentiment: CallSentiment = Field(..., description="Sentiment and tone analysis")
