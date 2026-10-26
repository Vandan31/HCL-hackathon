#!/usr/bin/env python3
"""Illustrative API/infrastructure cost estimator; never a live provider quote."""
import argparse
import json

def fraction(s):
    x=float(s)
    if not 0 <= x <= 1:
        raise argparse.ArgumentTypeError('Fraction must be in [0, 1]')
    return x

def nonnegative(s):
    x=float(s)
    if x < 0:
        raise argparse.ArgumentTypeError('Value must be nonnegative')
    return x

def estimate(requests, input_tokens, output_tokens, large_input, large_output,
             small_input, small_output, small_share, cache_hit, infra_day=0.0,
             retrieval_request=0.0, extra_requests=0.0):
    """Prices per million tokens; retrieval_request in $/request; return dict."""
    large=(input_tokens*large_input+output_tokens*large_output)/1_000_000
    small=(input_tokens*small_input+output_tokens*small_output)/1_000_000
    # Retries/extra attempts represented as fractional additional model calls for uncached requests.
    model_calls=requests*(1-cache_hit)*(1+extra_requests)
    baseline_model=requests*(1+extra_requests)*large
    optimized_model=model_calls*(small_share*small+(1-small_share)*large)
    # No unsupported precision claim: same retrieval and infra assumption in both scenarios.
    common=requests*retrieval_request + infra_day
    baseline=baseline_model+common
    optimized=optimized_model+common
    saved=baseline-optimized
    return {
        'assumptions': {'requests_per_day': requests, 'input_tokens': input_tokens,
                        'output_tokens': output_tokens, 'large_model_cost_per_call_usd': large,
                        'small_model_cost_per_call_usd': small, 'small_share_of_uncached': small_share,
                        'exact_cache_hit_rate': cache_hit, 'extra_model_attempts_per_uncached_request': extra_requests,
                        'fixed_infra_per_day_usd': infra_day, 'retrieval_per_request_usd': retrieval_request},
        'daily_baseline_usd': round(baseline, 6),
        'daily_optimized_usd': round(optimized, 6),
        'savings_per_day_usd': round(saved, 6),
        'savings_percent': round(saved / baseline * 100, 2) if baseline else 0,
        'optimized_usd_per_1000_requests': round(optimized / requests * 1000, 6) if requests else 0,
        'estimated_30day_optimized_usd': round(optimized*30, 2),
        'note': 'Illustrative cost scenario, not vendor price or measured workload. Compare coverage, model quality, and cache safety before deployment.'
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--requests', type=nonnegative, required=True, help='requests per day')
    p.add_argument('--input-tokens', type=nonnegative, required=True)
    p.add_argument('--output-tokens', type=nonnegative, required=True)
    p.add_argument('--large-input', type=nonnegative, required=True, help='USD per million input tokens')
    p.add_argument('--large-output', type=nonnegative, required=True, help='USD per million output tokens')
    p.add_argument('--small-input', type=nonnegative, required=True)
    p.add_argument('--small-output', type=nonnegative, required=True)
    p.add_argument('--small-share', type=fraction, default=0.8)
    p.add_argument('--cache-hit', type=fraction, default=0.0)
    p.add_argument('--infra-day', type=nonnegative, default=0.0)
    p.add_argument('--retrieval-request', type=nonnegative, default=0.0)
    p.add_argument('--extra-requests', type=nonnegative, default=0.0, help='extra model attempts per uncached request')
    a=p.parse_args()
    print(json.dumps(estimate(a.requests, a.input_tokens, a.output_tokens,
                              a.large_input, a.large_output, a.small_input,
                              a.small_output, a.small_share, a.cache_hit,
                              a.infra_day, a.retrieval_request, a.extra_requests), indent=2))

if __name__=='__main__': main()
