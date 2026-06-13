"""
Unit tests for LLM analyzer (OpenAI, Anthropic, Siemens AI)
"""
import pytest
from unittest.mock import Mock, patch
from app.llm.analyzer import LLMAnalyzer, analyze_with_llm


@pytest.mark.unit
@pytest.mark.llm
def test_llm_analyzer_initialization():
    """Test LLM analyzer initialization"""
    analyzer = LLMAnalyzer()
    assert analyzer.provider in ["openai", "anthropic", "siemens"]
    assert analyzer.model is not None
    assert analyzer.max_tokens > 0


@pytest.mark.unit
@pytest.mark.llm
def test_build_analysis_prompt(sample_crash_data):
    """Test prompt building"""
    analyzer = LLMAnalyzer()
    prompt = analyzer._build_analysis_prompt(sample_crash_data)
    
    assert "0xC0000005" in prompt
    assert "Access Violation" in prompt
    assert "myapp.exe" in prompt
    assert "ANALYSIS REQUIRED" in prompt


@pytest.mark.unit
@pytest.mark.llm
def test_format_stack_trace(sample_crash_data):
    """Test stack trace formatting"""
    analyzer = LLMAnalyzer()
    formatted = analyzer._format_stack_trace(sample_crash_data["stack_trace"])
    
    assert "myapp.exe" in formatted
    assert "main" in formatted
    assert "#00" in formatted


@pytest.mark.unit
@pytest.mark.llm
def test_parse_llm_response_valid(mock_llm_response):
    """Test parsing valid LLM response"""
    import json
    analyzer = LLMAnalyzer()
    response_json = json.dumps(mock_llm_response)
    
    parsed = analyzer._parse_llm_response(response_json)
    
    assert parsed["root_cause"] == mock_llm_response["root_cause"]
    assert parsed["severity"] == mock_llm_response["severity"]
    assert len(parsed["solutions"]) > 0
    assert 0 <= parsed["confidence_score"] <= 100


@pytest.mark.unit
@pytest.mark.llm
def test_parse_llm_response_invalid():
    """Test parsing invalid JSON response"""
    analyzer = LLMAnalyzer()
    invalid_json = "This is not JSON"
    
    parsed = analyzer._parse_llm_response(invalid_json)
    
    # Should return fallback analysis
    assert parsed["confidence_score"] == 0
    assert parsed["root_cause"].startswith("Analysis failed")


@pytest.mark.unit
@pytest.mark.llm
@patch('openai.chat.completions.create')
def test_analyze_with_openai_mock(mock_create, sample_crash_data, mock_llm_response):
    """Test OpenAI API call with mock"""
    import json
    
    # Mock OpenAI response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps(mock_llm_response)
    mock_create.return_value = mock_response
    
    analyzer = LLMAnalyzer()
    prompt = analyzer._build_analysis_prompt(sample_crash_data)
    result = analyzer._analyze_with_openai(prompt)
    
    assert result is not None
    mock_create.assert_called_once()


@pytest.mark.unit
@pytest.mark.llm
@patch('app.llm.analyzer.LLMAnalyzer.analyze_crash')
def test_analyze_with_llm_function(mock_analyze, sample_crash_data, mock_llm_response):
    """Test the convenience analyze_with_llm function"""
    mock_analyze.return_value = mock_llm_response
    
    result = analyze_with_llm(sample_crash_data)
    
    assert result == mock_llm_response
    mock_analyze.assert_called_once_with(sample_crash_data)


@pytest.mark.slow
@pytest.mark.llm
def test_analyze_crash_integration(sample_crash_data):
    """Integration test with real LLM API (requires API key)"""
    # This test only runs if explicitly requested and API key is configured
    import os
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    analyzer = LLMAnalyzer()
    result = analyzer.analyze_crash(sample_crash_data)
    
    assert "root_cause" in result
    assert "solutions" in result
    assert result["confidence_score"] > 0


@pytest.mark.unit
@pytest.mark.llm
def test_siemens_provider_initialization():
    """Test Siemens provider initialization"""
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.LLM_PROVIDER = "siemens"
        mock_settings.SIEMENS_API_KEY = "SIAK-test-key"
        mock_settings.LLM_BASE_URL = "https://api.siemens.com/llm/v1"
        mock_settings.LLM_MODEL = "qwen3-30b-a3b-instruct-2507"
        mock_settings.LLM_MAX_TOKENS = 4096
        mock_settings.LLM_TEMPERATURE = 0.3
        mock_settings.ENABLE_FUNCTION_CALLING = False
        
        analyzer = LLMAnalyzer()
        assert analyzer.provider == "siemens"


@pytest.mark.unit
@pytest.mark.llm  
def test_function_calling_enabled():
    """Test function calling feature flag"""
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.LLM_PROVIDER = "siemens"
        mock_settings.ENABLE_FUNCTION_CALLING = True
        mock_settings.SIEMENS_API_KEY = "test"
        mock_settings.LLM_BASE_URL = "https://api.siemens.com/llm/v1"
        mock_settings.LLM_MODEL = "qwen3-30b-a3b-instruct-2507"
        mock_settings.LLM_MAX_TOKENS = 4096
        mock_settings.LLM_TEMPERATURE = 0.3
        
        analyzer = LLMAnalyzer()
        # Function calling should be available for Siemens provider
        assert hasattr(analyzer, '_analyze_with_function_calling')


@pytest.mark.slow
@pytest.mark.llm
@pytest.mark.integration
def test_siemens_integration(sample_crash_data):
    """Integration test with Siemens AI (requires API key)"""
    import os
    if not os.getenv("SIEMENS_API_KEY"):
        pytest.skip("SIEMENS_API_KEY not set")
    
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.LLM_PROVIDER = "siemens"
        mock_settings.SIEMENS_API_KEY = os.getenv("SIEMENS_API_KEY")
        mock_settings.LLM_BASE_URL = "https://api.siemens.com/llm/v1"
        mock_settings.LLM_MODEL = "mistral-7b-instruct"
        mock_settings.LLM_MAX_TOKENS = 4096
        mock_settings.LLM_TEMPERATURE = 0.3
        mock_settings.ENABLE_FUNCTION_CALLING = False
        
        analyzer = LLMAnalyzer()
        result = analyzer.analyze_crash(sample_crash_data)
        
        assert "root_cause" in result
        assert "solutions" in result
        assert result["confidence_score"] > 0
        # Siemens should be free/low-cost
        assert analyzer.cost_usd <= 0.01

