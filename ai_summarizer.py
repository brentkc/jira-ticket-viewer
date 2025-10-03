"""
Real AI Ticket Triage Module for Jira Ticket Viewer
Uses GPT-4 with emotional intelligence for sophisticated ticket analysis
"""

import re
import json
import openai
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from ai_config import get_openai_api_key, AI_PROVIDER, OPENAI_MODEL, MAX_TOKENS, TEMPERATURE
from ai_settings import AISettings

class AITicketSummarizer:
    def __init__(self):
        self.client = None
        self.settings = AISettings()
        self.setup_ai_client()
        self.company_knowledge = self._load_company_knowledge()

    def _load_company_knowledge(self):
        """Load company knowledge base from file"""
        try:
            import os
            knowledge_file = os.path.join(os.path.dirname(__file__), 'company_knowledge.txt')
            if os.path.exists(knowledge_file):
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return ""
        except Exception as e:
            print(f"Could not load company knowledge: {e}")
            return ""

    def setup_ai_client(self):
        """Setup the AI client based on configuration"""
        if AI_PROVIDER == "openai":
            api_key = get_openai_api_key()
            if api_key:
                self.client = openai.OpenAI(api_key=api_key)
            else:
                print("⚠️ No OpenAI API key found. Using fallback mode.")

    def analyze_ticket(self, ticket_data: Dict[str, Any], additional_context: str = "") -> Dict[str, Any]:
        """
        Analyze ticket using real AI with emotional intelligence
        """
        try:
            # NO PRINT STATEMENTS - they cause encoding errors
            fields = ticket_data.get('fields', {})

            # Debug: Write raw data to file to see what we're dealing with
            with open('ticket_debug.txt', 'w', encoding='utf-8') as f:
                f.write("=== RAW TICKET DATA ===\n")
                f.write(f"Summary: {repr(fields.get('summary', ''))}\n")
                f.write(f"Description: {repr(fields.get('description', ''))}\n")
                f.write(f"Reporter: {repr(fields.get('reporter', {}))}\n")
                f.flush()

            summary = self._clean_text_for_encoding(fields.get('summary', ''))
            description = self._clean_text_for_encoding(self._extract_description_text(fields.get('description', '')))

            # Get basic ticket info for context
            ticket_key = self._clean_text_for_encoding(ticket_data.get('key', 'Unknown'))
            reporter = self._clean_text_for_encoding(fields.get('reporter', {}).get('displayName', 'Unknown'))
            priority = self._clean_text_for_encoding(fields.get('priority', {}).get('name', 'Not set'))
            status = self._clean_text_for_encoding(fields.get('status', {}).get('name', 'Unknown'))
            created = self._clean_text_for_encoding(fields.get('created', ''))

            # Format creation date
            created_readable = "Unknown"
            if created:
                try:
                    created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    created_readable = created_date.strftime('%Y-%m-%d at %H:%M')
                except:
                    created_readable = created

            # Only use AI - no rule-based fallback
            if self.client:
                return self._analyze_with_ai(ticket_key, summary, description, reporter, priority, status, created_readable, additional_context)
            else:
                # No API key configured
                return {
                    'ticket_type': 'error',
                    'has_sufficient_detail': False,
                    'triage_response': "❌ OpenAI API key not configured.\n\nPlease configure your API key in the application settings to use AI analysis.",
                    'existing_facts': [f"**Ticket:** {ticket_key}", f"**Reporter:** {reporter}", f"**Summary:** {summary}"],
                    'comments_facts': [],
                    'suggested_questions': [],
                    'summary_facts': [],
                    'emotional_state': 'Unknown',
                    'urgency_level': 3,
                    'confidence': 'error'
                }

        except Exception as e:
            import traceback
            error_msg = f"ENCODING ERROR AT START: {str(e)}\nTraceback: {traceback.format_exc()}"
            print(f"[AI DEBUG] IMMEDIATE ERROR: {error_msg}")
            return {
                'ticket_type': 'error',
                'has_sufficient_detail': False,
                'triage_response': f"ENCODING ERROR: {str(e)}",
                'existing_facts': [f"ERROR: {error_msg}"],
                'comments_facts': [],
                'suggested_questions': [],
                'summary_facts': [],
                'emotional_state': 'Error',
                'urgency_level': 1,
                'confidence': 'error'
            }

    def _analyze_with_ai(self, ticket_key, summary, description, reporter, priority, status, created, additional_context=""):
        """Use real AI (GPT-4) for sophisticated analysis"""

        # Prepare the context for AI
        context = f"""
Ticket: {ticket_key}
Summary: {summary}
Description: {description}
Reporter: {reporter}
Priority: {priority}
Status: {status}
Created: {created}
"""

        # Add additional context if provided
        if additional_context:
            context += f"\n**IMPORTANT CONTEXT FROM AGENT:** {additional_context}\n"

        # Add company knowledge base if available
        knowledge_section = ""
        if self.company_knowledge:
            knowledge_section = f"""
COMPANY KNOWLEDGE BASE:
{self.company_knowledge}

IMPORTANT: Use this knowledge base to:
- Check if existing subscriptions can meet software requests
- Understand org structure for access requests and approvals
- Follow company guidelines for hardware and software standards
- Recognize executives and their roles (e.g., CFO Natalie Chen)
"""

        # Smart triage prompt that differentiates request types and captures core functionality
        prompt = f"""You are an expert IT support specialist. Analyze this ticket and create a structured response based on the request type.

TICKET DETAILS:
{context}

{knowledge_section}

FIRST: Determine the ticket type:
1. NEW SOFTWARE REQUEST - User wants new software/tool/subscription
2. FAULT/ISSUE - Something is broken or not working
3. ACCESS REQUEST - User needs access/permissions to existing system
4. HOW-TO/TRAINING - User needs help using existing tools
5. HARDWARE REQUEST - User needs physical equipment
6. STATUS UPDATE/FYI - User is providing information, update, or notification (no action needed from support)
7. OTHER - General inquiry

RESPONSE STRATEGY BY TYPE:

For NEW SOFTWARE REQUESTS:
CRITICAL: Check the COMPANY KNOWLEDGE BASE for existing subscriptions first! The company already has many tools.
Focus on capturing:
1. CORE FUNCTIONALITY: What specific capabilities/features do you need? (Be precise - e.g., "screen recording with annotation" not just "recording")
2. EXISTING TOOLS CHECKED: Have you checked if [list relevant existing tools from knowledge base] can do this?
3. USE CASE: What business problem are you trying to solve? What's your workflow?
4. CURRENT WORKAROUND: How are you handling this now? What's not working about the current approach?
5. USERS & FREQUENCY: Who needs this and how often will it be used?
6. URGENCY: When do you need this capability by, and why that timeline?

If existing subscriptions can likely meet the need, mention this in your internal assessment.

For FAULTS/ISSUES:
Focus on troubleshooting:
1. EXACT SYMPTOMS: What exactly happens? Error messages? Screenshots?
2. WHEN: When did this start? Does it happen consistently or intermittently?
3. SCOPE: Who is affected? Just you or multiple users?
4. WHAT CHANGED: Did anything change before this started? (updates, new software, etc.)
5. BUSINESS IMPACT: How is this blocking your work?

For ACCESS REQUESTS:
1. SYSTEM/RESOURCE: What specifically do you need access to?
2. LEVEL OF ACCESS: What permissions/role do you need?
3. BUSINESS JUSTIFICATION: Why do you need this access? What will you do with it?
4. DURATION: Temporary or permanent?
5. URGENCY: When do you need this by and why?

For HOW-TO/TRAINING:
1. WHAT YOU'RE TRYING TO DO: What's your end goal?
2. WHAT YOU'VE TRIED: What steps have you already attempted?
3. WHERE YOU'RE STUCK: What specifically is confusing or not working?

For STATUS UPDATE/FYI:
These tickets are informational - the user is providing an update, not requesting help. Your response should:
1. Acknowledge the information
2. Thank them for keeping you informed
3. Offer to help if they need anything
4. Be brief and friendly
DO NOT ask clarifying questions unless something is genuinely unclear.
Example: "Hi [Name], Thank you for the update on the [item]. I've noted this in our system. Please let me know if you need any assistance once they arrive!"

IMPORTANT:
- Format response with clear bullet points that can be copied to Jira
- Be conversational but professional
- For software requests, emphasize capturing CORE FUNCTIONALITY so team can evaluate existing solutions
- Don't make timeline commitments

Format your response as JSON:
{{
    "emotional_state": "calm/frustrated/urgent/confused",
    "has_sufficient_detail": true/false,
    "triage_response": "Hi [Reporter Name],\\n\\nThank you for your [request/report]. To help find the best solution, I need a bit more information:\\n\\n[Numbered questions with blank lines for responses]\\n\\nExample format:\\n1. CORE FUNCTIONALITY: [Question]\\n   Your response: \\n\\n2. USE CASE: [Question]\\n   Your response: \\n\\n[Continue for each question]\\n\\nThis will help us determine if we have existing tools that can meet your needs or if we need to explore new options.\\n\\n[Your Name]",
    "key_facts": ["extracted facts from ticket"],
    "ticket_type": "software_request/fault_issue/access_request/how_to/hardware_request/status_update/other",
    "urgency_level": 1-5,
    "recommended_actions": ["Actions for support team - include checking existing subscriptions for software requests"],
    "confidence": "high/medium/low"
}}

CRITICAL FORMATTING RULES:
- For STATUS UPDATES: Keep response brief and friendly (1-2 sentences max), just acknowledge the info. DO NOT ask questions.
- For REQUESTS: After each question, add "Your response: " on a new line with double line break after it
- This gives customer clear space to type their answers
- DO NOT include "Best regards" in triage_response - signature will be added automatically
- Use numbered list format (1., 2., 3., etc) not bullet points for questions
- Keep questions conversational and clear
- Look for indicators like "I've ordered", "FYI", "update", "just letting you know" to identify status updates

Make the response ready to copy and paste."""

        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert IT support specialist with high emotional intelligence. Provide practical, empathetic responses."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )

            # Parse the AI response
            ai_response = response.choices[0].message.content

            # Try to extract JSON from the response
            try:
                # Look for JSON in the response
                json_start = ai_response.find('{')
                json_end = ai_response.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = ai_response[json_start:json_end]
                    ai_data = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")

            except (json.JSONDecodeError, ValueError):
                # If JSON parsing fails, create structured response from text
                ai_data = self._parse_ai_text_response(ai_response)

            # Format the triage response and internal assessment
            triage_response = self._format_triage_response(ai_data)
            internal_assessment = self._get_internal_assessment(ai_data)

            return {
                'ticket_type': ai_data.get('ticket_type', 'general_inquiry'),
                'has_sufficient_detail': ai_data.get('has_sufficient_detail', False),
                'triage_response': triage_response,
                'internal_assessment': internal_assessment,
                'existing_facts': self._format_facts(ai_data.get('key_facts', [])),
                'comments_facts': ["[AI] AI Analysis: Real-time using GPT-4o-mini"],
                'suggested_questions': self._get_ai_suggestions(ai_data),
                'summary_facts': self._create_ai_summary(ai_data),
                'emotional_state': ai_data.get('emotional_state', 'Unknown'),
                'urgency_level': ai_data.get('urgency_level', 3),
                'confidence': ai_data.get('confidence', 'medium')
            }

        except Exception as e:
            print(f"AI API Error: {str(e)}")
            # Return error instead of rule-based fallback
            return {
                'ticket_type': 'error',
                'has_sufficient_detail': False,
                'triage_response': f"❌ AI Analysis Failed: {str(e)}\n\nPlease check your OpenAI API key configuration and try again.",
                'existing_facts': [f"❌ Error: {str(e)}"],
                'comments_facts': [],
                'suggested_questions': [],
                'summary_facts': [],
                'emotional_state': 'Error',
                'urgency_level': 1,
                'confidence': 'error'
            }

    def _format_triage_response(self, ai_data):
        """Format the AI triage response - clean customer-facing version"""

        response = ai_data.get('triage_response', '')
        response = self._clean_text_for_encoding(response)

        # Get user's signature from settings
        signature = self.settings.get_signature_block()

        # Remove any AI-generated signatures
        # Common patterns to remove
        signature_patterns = [
            "Best regards,",
            "Kind regards,",
            "Regards,",
            "Thanks,",
            "Thank you,",
            "[Your Name]"
        ]

        for pattern in signature_patterns:
            if pattern in response:
                # Split and take everything before the signature
                response = response.split(pattern)[0].strip()

        # Post-process: Add proper formatting for questions with response spaces
        # Look for numbered questions (1., 2., etc.) and ensure they have proper spacing
        import re

        # Add line break before each numbered item
        response = re.sub(r'(\d+\.)', r'\n\n\1', response)

        # Ensure "Your response:" is on its own line with blank line after it
        # First, add line break before "Your response:"
        response = re.sub(r'(\?|\.)\s*Your response:', r'\1\n   Your response:', response)

        # Then ensure blank line after "Your response:"
        response = re.sub(r'Your response:\s*(?!\n\n)', 'Your response:\n\n', response)

        # Clean up any multiple blank lines (more than 2 consecutive newlines)
        response = re.sub(r'\n{3,}', '\n\n', response)

        # Clean up leading whitespace
        response = response.strip()

        # Add proper signature at the end
        response = f"{response}\n\n{signature}"

        # Return just the customer-facing response
        return response

    def _get_internal_assessment(self, ai_data):
        """Get internal assessment for agent use only (not customer-facing)"""

        emotional_state = ai_data.get('emotional_state', 'Unknown')
        has_detail = ai_data.get('has_sufficient_detail', False)
        urgency = ai_data.get('urgency_level', 3)
        confidence = ai_data.get('confidence', 'unknown')
        ticket_type = ai_data.get('ticket_type', 'general_inquiry').replace('_', ' ').title()

        assessment = f"""INTERNAL ASSESSMENT (DO NOT SEND TO CUSTOMER)
{'=' * 50}

Ticket Type: {ticket_type}
Emotional State: {emotional_state}
Urgency Level: {urgency}/5
AI Confidence: {confidence.title()}
Has Sufficient Detail: {'Yes' if has_detail else 'No'}

Status: {'Ready to Process' if has_detail else 'Needs More Information'}
"""

        if ai_data.get('recommended_actions'):
            assessment += "\nRecommended Actions:\n"
            for action in ai_data['recommended_actions']:
                assessment += f"  - {action}\n"

        return assessment

    def _parse_ai_text_response(self, text):
        """Parse AI response when JSON extraction fails"""
        return {
            'emotional_state': 'Neutral',
            'has_sufficient_detail': 'sufficient' in text.lower(),
            'triage_response': text[:500] + "..." if len(text) > 500 else text,
            'key_facts': [text[:200] + "..." if len(text) > 200 else text],
            'ticket_type': 'general_inquiry',
            'urgency_level': 3,
            'recommended_actions': ['Review ticket details', 'Contact reporter if needed'],
            'confidence': 'low'
        }


    def _format_facts(self, facts_list):
        """Format facts from AI response"""
        if isinstance(facts_list, list):
            return [f"[SEARCH] {self._clean_text_for_encoding(fact)}" for fact in facts_list]
        return ["[SEARCH] Facts analysis not available"]

    def _get_ai_suggestions(self, ai_data):
        """Get AI suggestions for follow-up"""
        actions = ai_data.get('recommended_actions', [])
        return [f"[IDEA] {self._clean_text_for_encoding(action)}" for action in actions] if actions else []

    def _create_ai_summary(self, ai_data):
        """Create AI-powered summary"""
        summary = []
        summary.append(f"[AI] **AI Confidence:** {ai_data.get('confidence', 'Unknown').title()}")
        summary.append(f"[HAPPY] **Emotional State:** {ai_data.get('emotional_state', 'Unknown')}")
        summary.append(f"[ALERT] **Urgency Level:** {ai_data.get('urgency_level', 'Unknown')}/5")
        summary.append(f"[FOLDER] **Category:** {ai_data.get('ticket_type', 'Unknown').replace('_', ' ').title()}")

        if ai_data.get('key_facts'):
            summary.extend([f"[LIST] {self._clean_text_for_encoding(fact)}" for fact in ai_data['key_facts']])

        return summary

    def _extract_description_text(self, description) -> str:
        """Extract plain text from Jira description format"""
        if isinstance(description, dict):
            # Handle ADF (Atlassian Document Format)
            text_parts = []

            def extract_text_recursive(obj):
                if isinstance(obj, dict):
                    if obj.get('type') == 'text':
                        text = obj.get('text', '')
                        # Clean text to avoid encoding issues
                        text = self._clean_text_for_encoding(text)
                        text_parts.append(text)
                    elif 'content' in obj:
                        for item in obj['content']:
                            extract_text_recursive(item)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_text_recursive(item)

            extract_text_recursive(description)
            return ' '.join(text_parts)

        return self._clean_text_for_encoding(str(description)) if description else ''

    def _clean_text_for_encoding(self, text):
        """Clean text to avoid Windows encoding issues"""
        if not isinstance(text, str):
            text = str(text)

        # ULTRA AGGRESSIVE: Handle encoding errors immediately
        try:
            # Try to encode to see if there are issues
            text.encode('cp1252')
        except UnicodeEncodeError:
            # If it fails, be super aggressive
            safe_chars = []
            for char in text:
                try:
                    char.encode('cp1252')
                    safe_chars.append(char)
                except UnicodeEncodeError:
                    safe_chars.append(' ')  # Replace problematic chars with space
            text = ''.join(safe_chars)

        # SUPER AGGRESSIVE: Strip ALL non-printable ASCII
        clean_text = ""
        for char in text:
            char_code = ord(char)
            if 32 <= char_code <= 126:  # Only printable ASCII characters
                clean_text += char
            elif char_code in [9, 10, 13]:  # Tab, newline, carriage return
                clean_text += char
            else:
                # Replace everything else with space
                clean_text += " "

        # Remove multiple spaces
        import re
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        return clean_text


def format_analysis_for_display(analysis: Dict[str, Any]) -> str:
    """Format the AI analysis for display in the dialog"""

    output = []

    # Header with AI branding
    output.append("🤖 **REAL AI TRIAGE ANALYSIS**")
    output.append("Powered by GPT-4 with Emotional Intelligence")
    output.append("=" * 50)
    output.append("")

    # AI confidence and emotional assessment
    if 'emotional_state' in analysis:
        output.append(f"😊 **Emotional State:** {analysis['emotional_state']}")
        output.append(f"🚨 **Urgency Level:** {analysis.get('urgency_level', 'Unknown')}/5")
        output.append(f"🎯 **AI Confidence:** {analysis.get('confidence', 'Unknown').title()}")
        output.append("")

    # Ticket classification
    output.append(f"📂 **Ticket Type:** {analysis['ticket_type'].replace('_', ' ').title()}")
    output.append(f"✅ **Has Sufficient Detail:** {'Yes' if analysis['has_sufficient_detail'] else 'No'}")
    output.append("")

    # AI triage response
    output.append("🧠 **AI TRIAGE RESPONSE**")
    output.append("-" * 30)
    output.append(analysis['triage_response'])
    output.append("")

    # Current facts
    if analysis['existing_facts']:
        output.append("📊 **EXTRACTED FACTS**")
        output.append("-" * 30)
        for fact in analysis['existing_facts']:
            output.append(fact)
        output.append("")

    # AI suggestions
    if analysis.get('suggested_questions'):
        output.append("💡 **AI RECOMMENDATIONS**")
        output.append("-" * 30)
        for suggestion in analysis['suggested_questions']:
            output.append(suggestion)
        output.append("")

    output.append("---")
    output.append("🚀 **Tip:** This analysis was generated by GPT-4. Copy the triage response above and paste it into the ticket.")

    return "\n".join(output)