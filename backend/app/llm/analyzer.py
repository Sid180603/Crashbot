"""
PHASE 2: LLM Integration
OpenAI GPT-4 / Claude / Siemens AI integration for crash analysis
"""
import openai
import anthropic
import json
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# LLM Pricing (per 1K tokens)
LLM_PRICING = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    # Siemens AI Models (Free/Low-cost for internal use)
    "qwen3-30b-a3b-instruct-2507": {"input": 0.0, "output": 0.0},
    "qwen3-30b-a3b-thinking-2507": {"input": 0.0, "output": 0.0},
    "qwen3-30b-a3b": {"input": 0.0, "output": 0.0},
    "devstral-small-2505": {"input": 0.0, "output": 0.0},
    "devstral-medium-2507": {"input": 0.0, "output": 0.0},
    "mistral-7b-instruct": {"input": 0.0, "output": 0.0},
    "deepseek-r1-0528-qwen3-8b": {"input": 0.0, "output": 0.0},
    "qwen3-coder-30b-a3b-instruct": {"input": 0.0, "output": 0.0},
}


class LLMAnalyzer:
    """LLM-based crash analyzer"""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE
        self.cost_usd = 0.0
        self.tokens_used = {"input": 0, "output": 0}
        self.openai_client = None
        
        if self.provider == "openai":
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "anthropic":
            self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif self.provider == "siemens":
            # Siemens uses OpenAI-compatible API
            self.openai_client = openai.OpenAI(
                api_key=settings.SIEMENS_API_KEY,
                base_url=settings.LLM_BASE_URL,
            )
            logger.info(f"Initialized Siemens AI provider with base URL: {settings.LLM_BASE_URL}")
    
    def analyze_crash(self, crash_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze crash using LLM
        
        Args:
            crash_data: Parsed crash dump data
            
        Returns:
            Analysis results with root cause, solutions, etc.
        """
        logger.info(f"Starting LLM analysis with {self.provider}/{self.model}")
        start_time = time.time()
        
        try:
            # Build prompt
            prompt = self._build_analysis_prompt(crash_data)
            
            # Call LLM (Siemens uses OpenAI-compatible API)
            if self.provider in ["openai", "siemens"]:
                if settings.ENABLE_FUNCTION_CALLING and self.provider == "siemens":
                    result = self._analyze_with_function_calling(prompt)
                else:
                    result = self._analyze_with_openai(prompt)
            elif self.provider == "anthropic":
                result = self._analyze_with_claude(prompt)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
            
            # Parse response
            analysis = self._parse_llm_response(result)
            
            duration = time.time() - start_time
            logger.info(f"LLM analysis complete in {duration:.2f}s")
            
            return analysis
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}", exc_info=True)
            raise
    
    def _build_analysis_prompt(self, crash_data: Dict[str, Any]) -> str:
        """Build structured prompt for LLM"""
        
        # Extract key information
        exception_code = crash_data.get("exception_code", "Unknown")
        exception_msg = crash_data.get("exception_message", "")
        module = crash_data.get("faulting_module", "Unknown")
        address = crash_data.get("faulting_address", "")
        stack_trace = crash_data.get("stack_trace", [])
        platform = crash_data.get("platform", "Unknown")
        arch = crash_data.get("architecture", "Unknown")
        
        # Format stack trace
        stack_str = self._format_stack_trace(stack_trace)
        
        prompt = f"""You are an expert crash dump analyzer. Analyze the following crash and provide actionable insights.

CRASH INFORMATION:
------------------
Platform: {platform}
Architecture: {arch}
Exception Code: {exception_code}
Exception Message: {exception_msg}
Faulting Module: {module}
Faulting Address: {address}

STACK TRACE:
-----------
{stack_str}

ANALYSIS REQUIRED:
-----------------
Provide your analysis in the following JSON format:

{{
    "root_cause": "One-sentence summary of the root cause",
    "explanation": "Detailed technical explanation of what happened and why",
    "solutions": [
        {{
            "title": "Solution title",
            "description": "Detailed description",
            "priority": 1-5 (1=highest),
            "code_example": "Optional code example or null"
        }}
    ],
    "severity": "critical|high|medium|low",
    "confidence_score": 0-100 (your confidence in this analysis),
    "references": ["URL1", "URL2"] (relevant documentation/forum posts)
}}

GUIDELINES:
- Be specific and technical
- Prioritize solutions by likelihood of fixing the issue
- Include code examples where helpful
- Reference official documentation when possible
- Consider common causes for this exception type
- Explain in terms developers can understand and act on

Provide ONLY the JSON response, no additional text.
"""
        return prompt
    
    def _format_stack_trace(self, stack_trace: List[Dict], max_frames: int = 20) -> str:
        """Format stack trace for prompt"""
        if not stack_trace:
            return "No stack trace available"
        
        lines = []
        for i, frame in enumerate(stack_trace[:max_frames]):
            module = frame.get("module", "Unknown")
            function = frame.get("function", "Unknown")
            offset = frame.get("offset", "0x0")
            address = frame.get("address", "")
            
            lines.append(f"#{i:02d} {address} {module}!{function}{offset}")
        
        if len(stack_trace) > max_frames:
            lines.append(f"... ({len(stack_trace) - max_frames} more frames)")
        
        return "\n".join(lines)
    
    def _analyze_with_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert crash dump analyzer specializing in Windows, Linux, and cross-platform debugging."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}  # Ensure JSON response
            )
            
            # Track token usage and cost
            if response.usage:
                self.tokens_used["input"] = response.usage.prompt_tokens
                self.tokens_used["output"] = response.usage.completion_tokens
                self.cost_usd = self._calculate_cost(
                    self.model,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
                logger.info(
                    f"{self.provider.upper()} API usage: {response.usage.prompt_tokens} input + "
                    f"{response.usage.completion_tokens} output = ${self.cost_usd:.4f}"
                )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"{self.provider.upper()} API call failed: {e}")
            raise
    
    def _analyze_with_claude(self, prompt: str) -> str:
        """Call Anthropic Claude API"""
        try:
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system="You are an expert crash dump analyzer specializing in Windows, Linux, and cross-platform debugging. Always respond with valid JSON.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Track token usage and cost
            if response.usage:
                self.tokens_used["input"] = response.usage.input_tokens
                self.tokens_used["output"] = response.usage.output_tokens
                self.cost_usd = self._calculate_cost(
                    self.model,
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )
                logger.info(
                    f"Claude API usage: {response.usage.input_tokens} input + "
                    f"{response.usage.output_tokens} output = ${self.cost_usd:.4f}"
                )
            
            # Extract text content from response
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate LLM API cost based on token usage"""
        if model not in LLM_PRICING:
            logger.warning(f"Unknown model pricing for {model}, using default")
            return 0.0
        
        pricing = LLM_PRICING[model]
        input_cost = (input_tokens / 1000.0) * pricing["input"]
        output_cost = (output_tokens / 1000.0) * pricing["output"]
        return input_cost + output_cost
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate LLM JSON response"""
        try:
            data = json.loads(response)
            
            # Validate required fields
            required = ["root_cause", "explanation", "solutions", "severity", "confidence_score"]
            for field in required:
                if field not in data:
                    logger.warning(f"Missing field in LLM response: {field}")
            
            # Ensure solutions is a list
            if not isinstance(data.get("solutions"), list):
                data["solutions"] = []
            
            # Ensure references is a list
            if "references" not in data or not isinstance(data["references"], list):
                data["references"] = []
            
            # Clamp confidence score
            if "confidence_score" in data:
                data["confidence_score"] = max(0, min(100, data["confidence_score"]))
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response: {response}")
            
            # Return fallback analysis
            return {
                "root_cause": "Analysis failed - unable to parse LLM response",
                "explanation": response,
                "solutions": [],
                "severity": "unknown",
                "confidence_score": 0,
                "references": []
            }
    
    def _analyze_with_function_calling(self, prompt: str) -> str:
        """
        Use function calling for structured crash analysis (Siemens AI)
        Provides better structured output than JSON mode
        """
        try:
            # Define function schema for crash analysis
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "analyze_crash",
                        "description": "Analyze a crash dump and provide structured results with root cause, solutions, and severity",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "root_cause": {
                                    "type": "string",
                                    "description": "One-sentence summary of the root cause"
                                },
                                "explanation": {
                                    "type": "string",
                                    "description": "Detailed technical explanation of what happened and why"
                                },
                                "severity": {
                                    "type": "string",
                                    "enum": ["critical", "high", "medium", "low"],
                                    "description": "Severity level of the crash"
                                },
                                "confidence_score": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 100,
                                    "description": "Confidence in the analysis (0-100)"
                                },
                                "solutions": {
                                    "type": "array",
                                    "description": "List of potential solutions",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "title": {
                                                "type": "string",
                                                "description": "Solution title"
                                            },
                                            "description": {
                                                "type": "string",
                                                "description": "Detailed description of the solution"
                                            },
                                            "priority": {
                                                "type": "integer",
                                                "minimum": 1,
                                                "maximum": 5,
                                                "description": "Priority (1=highest, 5=lowest)"
                                            },
                                            "code_example": {
                                                "type": "string",
                                                "description": "Optional code example"
                                            }
                                        },
                                        "required": ["title", "description", "priority"]
                                    }
                                },
                                "references": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Relevant URLs for documentation or forum posts"
                                }
                            },
                            "required": ["root_cause", "explanation", "severity", "confidence_score", "solutions"]
                        }
                    }
                }
            ]
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert crash dump analyzer specializing in Windows, Linux, and cross-platform debugging."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "analyze_crash"}},
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Track usage
            if response.usage:
                self.tokens_used["input"] = response.usage.prompt_tokens
                self.tokens_used["output"] = response.usage.completion_tokens
                self.cost_usd = self._calculate_cost(
                    self.model,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
                logger.info(
                    f"{self.provider.upper()} API (Function Calling) usage: {response.usage.prompt_tokens} input + "
                    f"{response.usage.completion_tokens} output = ${self.cost_usd:.4f}"
                )
            
            # Extract function call result
            if response.choices[0].message.tool_calls:
                function_args = response.choices[0].message.tool_calls[0].function.arguments
                logger.info("Function calling returned structured output")
                return function_args
            else:
                # Fallback to regular content
                return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Function calling failed: {e}, falling back to regular mode")
            # Fallback to regular OpenAI call
            return self._analyze_with_openai(prompt)
    
    async def analyze_crash_ensemble(self, crash_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze crash with multiple models for consensus
        Provides higher confidence through model agreement
        """
        if not settings.ENABLE_MULTI_MODEL_ENSEMBLE:
            # If ensemble disabled, use regular analysis
            return self.analyze_crash(crash_data)
        
        logger.info("Starting multi-model ensemble analysis")
        start_time = time.time()
        
        try:
            # Parse ensemble models from config
            models = [m.strip() for m in settings.ENSEMBLE_MODELS.split(",")]
            logger.info(f"Using ensemble models: {models}")
            
            # Analyze with each model
            results = []
            for model in models:
                try:
                    analyzer = LLMAnalyzer()
                    analyzer.model = model
                    analyzer.provider = settings.LLM_PROVIDER
                    
                    result = analyzer.analyze_crash(crash_data)
                    result["model"] = model
                    results.append(result)
                    logger.info(f"Model {model} completed analysis")
                except Exception as e:
                    logger.error(f"Model {model} failed: {e}")
                    continue
            
            if len(results) < settings.ENSEMBLE_MIN_CONSENSUS:
                logger.warning(
                    f"Not enough models completed ({len(results)}/{settings.ENSEMBLE_MIN_CONSENSUS}), "
                    "using single model"
                )
                return self.analyze_crash(crash_data)
            
            # Aggregate results
            aggregated = self._aggregate_ensemble_results(results)
            
            duration = time.time() - start_time
            logger.info(f"Ensemble analysis complete in {duration:.2f}s with {len(results)} models")
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Ensemble analysis failed: {e}, falling back to single model")
            return self.analyze_crash(crash_data)
    
    def _aggregate_ensemble_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from multiple models
        Uses voting for categorical fields and averaging for numerical
        """
        if not results:
            raise ValueError("No results to aggregate")
        
        # Use most common root cause
        root_causes = [r.get("root_cause", "") for r in results]
        root_cause = max(set(root_causes), key=root_causes.count)
        
        # Use most common severity
        severities = [r.get("severity", "medium") for r in results]
        severity = max(set(severities), key=severities.count)
        
        # Average confidence scores
        confidence_scores = [r.get("confidence_score", 0) for r in results]
        avg_confidence = sum(confidence_scores) // len(confidence_scores)
        
        # Combine explanations (from highest confidence model)
        best_result = max(results, key=lambda x: x.get("confidence_score", 0))
        explanation = best_result.get("explanation", "")
        
        # Merge solutions (deduplicate by title)
        all_solutions = []
        seen_titles = set()
        for result in results:
            for solution in result.get("solutions", []):
                title = solution.get("title", "")
                if title and title not in seen_titles:
                    all_solutions.append(solution)
                    seen_titles.add(title)
        
        # Sort solutions by priority
        all_solutions.sort(key=lambda x: x.get("priority", 5))
        
        # Merge references
        all_references = []
        for result in results:
            all_references.extend(result.get("references", []))
        unique_references = list(set(all_references))
        
        return {
            "root_cause": root_cause,
            "explanation": explanation,
            "solutions": all_solutions[:10],  # Top 10 solutions
            "severity": severity,
            "confidence_score": avg_confidence,
            "references": unique_references,
            "ensemble_models": [r.get("model") for r in results],
            "ensemble_agreement": len(set(root_causes)) == 1  # All models agree
        }


def analyze_with_llm(crash_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to analyze crash with LLM
    Used in Phase 2 integration
    """
    analyzer = LLMAnalyzer()
    return analyzer.analyze_crash(crash_data)
