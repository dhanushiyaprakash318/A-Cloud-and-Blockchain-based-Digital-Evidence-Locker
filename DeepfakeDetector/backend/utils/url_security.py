"""
URL Security Intelligence Module
Detects phishing, malicious URLs, and suspicious patterns
"""

import re
from urllib.parse import urlparse
from typing import Dict, List
import socket

class URLSecurity:
    """Analyzes URLs for security threats and suspicious patterns"""
    
    def __init__(self):
        # Suspicious TLDs commonly used in phishing
        self.suspicious_tlds = [
            '.tk', '.ml', '.ga', '.cf', '.gq',  # Free domains
            '.top', '.xyz', '.club', '.work', '.click',
            '.link', '.download', '.stream'
        ]
        
        # Phishing keywords
        self.phishing_keywords = [
            'verify', 'account', 'update', 'confirm', 'login',
            'signin', 'banking', 'secure', 'suspended', 'locked',
            'unusual', 'activity', 'alert', 'warning', 'urgent',
            'password', 'credential', 'validate', 'restore', 'kyc',
            'prize', 'claim', 'refund', 'support-team', 'customer-support'
        ]
        
        # Legitimate domains (whitelist) - Global brands
        self.trusted_domains = [
            'google.com', 'youtube.com', 'facebook.com', 'twitter.com',
            'instagram.com', 'github.com', 'dropbox.com', 'drive.google.com',
            'imgur.com', 'reddit.com', 'linkedin.com', 'microsoft.com',
            'apple.com', 'amazon.com', 'netflix.com', 'amazon.in'
        ]
        
        # Protected brands database - Indian specific
        self.protected_brands = {
            # Indian Banks
            'banks': [
                'sbi', 'icici', 'hdfc', 'axis', 'kotak', 'pnb', 'bob', 
                'canara', 'union', 'indian', 'idbi', 'yes', 'indusind',
                'rbl', 'federal', 'bandhan', 'idfc'
            ],
            # Payment Apps
            'payments': [
                'paytm', 'phonepe', 'gpay', 'googlepay', 'bhim', 'mobikwik',
                'freecharge', 'amazonpay', 'whatsapp-pay', 'cred'
            ],
            # Government & ID
            'government': [
                'aadhaar', 'uidai', 'pan', 'passport', 'gov', 'india',
                'nsdl', 'utiitsl', 'incometax', 'gst', 'epfo', 'uan'
            ],
            # E-commerce
            'ecommerce': [
                'flipkart', 'myntra', 'snapdeal', 'meesho', 'ajio',
                'nykaa', 'bigbasket', 'grofers', 'swiggy', 'zomato'
            ],
            # Delivery & Logistics
            'delivery': [
                'dhl', 'fedex', 'bluedart', 'dtdc', 'indiapost', 'ecom-express'
            ],
            # Job Portals & Companies
            'jobs': [
                'tcs', 'infosys', 'wipro', 'cognizant', 'hcl', 'tech-mahindra',
                'naukri', 'linkedin', 'indeed', 'monster', 'shine'
            ],
            # Email & Social
            'email_social': [
                'gmail', 'outlook', 'yahoo', 'hotmail', 'facebook', 
                'instagram', 'whatsapp', 'telegram'
            ],
            # Scholarships & Education
            'education': [
                'scholarship', 'ugc', 'aicte', 'cbse', 'icse', 'neet', 'jee'
            ]
        }
        
        # Official domain mappings (brand -> official domains)
        self.official_domains = {
            # Indian Banks - Include .bank.in domains
            'sbi': ['onlinesbi.sbi', 'sbi.co.in', 'onlinesbi.com', 'sbi.bank.in', 'www.sbi.bank.in'],
            'icici': ['icicibank.com', 'icicidirect.com', 'icici.com', 'icici.bank.in', 'www.icici.bank.in'],
            'hdfc': ['hdfcbank.com', 'hdfclife.com', 'hdfc.com', 'hdfcbank.in', 'hdfc.bank.in'],
            'axis': ['axisbank.com', 'axis.bank.in', 'axisbank.co.in'],
            'kotak': ['kotak.com', 'kotakbank.com', 'kotak.bank.in'],
            'pnb': ['pnbindia.in', 'pnb.bank.in', 'netpnb.com'],
            # Payment Apps
            'paytm': ['paytm.com', 'paytmmall.com'],
            'phonepe': ['phonepe.com', 'www.phonepe.com'],
            'gpay': ['pay.google.com', 'google.com/pay'],
            # Government
            'aadhaar': ['uidai.gov.in', 'www.uidai.gov.in'],
            'pan': ['incometaxindiaefiling.gov.in', 'tin.tin.nsdl.com', 'incometax.gov.in'],
            # E-commerce
            'flipkart': ['flipkart.com', 'www.flipkart.com'],
            'amazon': ['amazon.in', 'amazon.com', 'www.amazon.in'],
            # IT Companies
            'tcs': ['tcs.com', 'www.tcs.com'],
            'infosys': ['infosys.com', 'www.infosys.com'],
            'wipro': ['wipro.com', 'www.wipro.com'],
            # Email & Social
            'gmail': ['gmail.com', 'google.com', 'mail.google.com'],
            'facebook': ['facebook.com', 'fb.com', 'www.facebook.com'],
            'instagram': ['instagram.com', 'www.instagram.com']
        }
    
    def analyze_url(self, url: str, redirect_chain: List[str] = None) -> Dict:
        """
        Comprehensive URL security analysis
        Returns: {
            'risk_score': int (0-100),
            'risk_level': str ('safe', 'low', 'medium', 'high', 'critical'),
            'flags': List[str],
            'is_phishing': bool,
            'is_malicious': bool,
            'details': dict
        }
        """
        flags = []
        risk_score = 0
        details = {}
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
            
            # 1. Check if trusted domain
            is_trusted = any(trusted in domain for trusted in self.trusted_domains)
            if is_trusted:
                details['trusted_domain'] = True
                return {
                    'risk_score': 0,
                    'risk_level': 'safe',
                    'flags': ['Trusted Domain'],
                    'is_phishing': False,
                    'is_malicious': False,
                    'details': details
                }
            
            # 2. Check for IP address instead of domain
            if self._is_ip_address(domain):
                flags.append('IP Address URL (Suspicious)')
                risk_score += 30
                details['ip_based'] = True
            
            # 3. Check for suspicious TLD
            for tld in self.suspicious_tlds:
                if domain.endswith(tld):
                    flags.append(f'Suspicious TLD: {tld}')
                    risk_score += 25
                    details['suspicious_tld'] = tld
                    break
            
            # 4. Check for missing HTTPS
            if parsed.scheme == 'http':
                flags.append('No HTTPS (Insecure)')
                risk_score += 15
                details['no_https'] = True
            
            # 5. Check for phishing keywords in URL
            url_lower = url.lower()
            found_keywords = [kw for kw in self.phishing_keywords if kw in url_lower]
            if found_keywords:
                flags.append(f'Phishing Keywords: {", ".join(found_keywords[:3])}')
                risk_score += len(found_keywords) * 10
                details['phishing_keywords'] = found_keywords
            
            # 6. Check for excessive subdomains
            subdomain_count = domain.count('.')
            if subdomain_count > 3:
                flags.append(f'Excessive Subdomains ({subdomain_count})')
                risk_score += 15
                details['subdomain_count'] = subdomain_count
            
            # 7. Check for homograph attacks (unicode lookalikes)
            if self._has_unicode_chars(domain):
                flags.append('Unicode Characters (Possible Homograph Attack)')
                risk_score += 35
                details['unicode_domain'] = True
            
            # 8. Check for suspicious patterns in domain
            if self._has_suspicious_patterns(domain):
                flags.append('Suspicious Domain Pattern')
                risk_score += 20
                details['suspicious_pattern'] = True
            
            # 9. Check redirect chain if provided
            if redirect_chain and len(redirect_chain) > 1:
                redirect_count = len(redirect_chain) - 1
                if redirect_count > 5:
                    flags.append(f'Excessive Redirects ({redirect_count})')
                    risk_score += 25
                    details['excessive_redirects'] = redirect_count
                elif redirect_count > 2:
                    flags.append(f'Multiple Redirects ({redirect_count})')
                    risk_score += 10
                    details['redirect_count'] = redirect_count
                
                # Check for cross-domain redirects
                domains_in_chain = [urlparse(u).netloc for u in redirect_chain]
                unique_domains = len(set(domains_in_chain))
                if unique_domains > 3:
                    flags.append(f'Cross-Domain Redirects ({unique_domains} domains)')
                    risk_score += 20
                    details['cross_domain_redirects'] = unique_domains
            
            # 10. Check URL length (very long URLs can be suspicious)
            if len(url) > 200:
                flags.append('Unusually Long URL')
                risk_score += 10
                details['long_url'] = len(url)
            
            # 11. Check for @ symbol (can hide real domain)
            if '@' in url:
                flags.append('@ Symbol in URL (Obfuscation)')
                risk_score += 30
                details['url_obfuscation'] = True
            
            # 12. Check for brand impersonation (CRITICAL - DYNAMIC SCORING)
            brand_check = self._check_brand_impersonation(domain)
            if brand_check['is_impersonation']:
                brand = brand_check['brand'].upper()
                category = brand_check['category']
                
                # DYNAMIC RISK SCORING based on severity
                base_brand_penalty = 40
                
                # Higher penalty for critical categories
                if category in ['banks', 'payments', 'government']:
                    base_brand_penalty = 50  # Critical financial/government
                elif category in ['email_social', 'jobs']:
                    base_brand_penalty = 45  # High-value targets
                else:
                    base_brand_penalty = 40  # Other brands
                
                # Additional penalty for multiple phishing keywords
                keyword_count = len(details.get('phishing_keywords', []))
                if keyword_count >= 3:
                    base_brand_penalty += 20  # Very suspicious
                elif keyword_count >= 2:
                    base_brand_penalty += 15  # Suspicious
                elif keyword_count >= 1:
                    base_brand_penalty += 10  # Moderately suspicious
                
                # Additional penalty for suspicious TLDs
                if details.get('suspicious_tld'):
                    base_brand_penalty += 15  # Free domain + brand = very bad
                
                # Additional penalty for no HTTPS
                if details.get('no_https'):
                    base_brand_penalty += 10  # Insecure + brand = suspicious
                
                flags.append(f"⚠️ BRAND IMPERSONATION: {brand}")
                flags.append(f"Fake {category} website detected")
                if brand_check['official_domains']:
                    flags.append(f"Official: {brand_check['official_domains'][0]}")
                
                risk_score += base_brand_penalty
                details['brand_impersonation'] = brand_check
                details['brand_penalty'] = base_brand_penalty

            
            # Cap risk score at 100
            risk_score = min(risk_score, 100)
            
            # Determine risk level
            if risk_score >= 70:
                risk_level = 'critical'
            elif risk_score >= 50:
                risk_level = 'high'
            elif risk_score >= 30:
                risk_level = 'medium'
            elif risk_score >= 10:
                risk_level = 'low'
            else:
                risk_level = 'safe'
            
            # Determine if phishing/malicious
            is_phishing = risk_score >= 50 or len(found_keywords) >= 3
            is_malicious = risk_score >= 70
            
            if not flags:
                flags.append('No Suspicious Indicators')
            
            return {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'flags': flags,
                'is_phishing': is_phishing,
                'is_malicious': is_malicious,
                'details': details
            }
            
        except Exception as e:
            print(f"URL security analysis error: {e}")
            return {
                'risk_score': 0,
                'risk_level': 'unknown',
                'flags': ['Analysis Error'],
                'is_phishing': False,
                'is_malicious': False,
                'details': {'error': str(e)}
            }
    
    def _is_ip_address(self, domain: str) -> bool:
        """Check if domain is an IP address"""
        # Remove port if present
        domain = domain.split(':')[0]
        
        # Check IPv4
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ipv4_pattern, domain):
            return True
        
        # Check IPv6 (simplified)
        if ':' in domain and not domain.startswith('['):
            return True
        
        return False
    
    def _has_unicode_chars(self, domain: str) -> bool:
        """Check for non-ASCII characters (homograph attack)"""
        try:
            domain.encode('ascii')
            return False
        except UnicodeEncodeError:
            return True
    
    def _has_suspicious_patterns(self, domain: str) -> bool:
        """Check for suspicious patterns in domain name"""
        suspicious_patterns = [
            r'\d{4,}',  # 4+ consecutive digits
            r'(.)\1{3,}',  # Same character repeated 4+ times
            r'-{2,}',  # Multiple consecutive hyphens
            r'[0-9]+[a-z]+[0-9]+',  # Numbers-letters-numbers pattern
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, domain):
                return True
        
        return False
    
    def _check_brand_impersonation(self, domain: str) -> Dict:
        """
        Check if domain is impersonating a protected brand
        Returns: {
            'is_impersonation': bool,
            'brand': str,
            'category': str,
            'official_domains': List[str]
        }
        """
        domain_lower = domain.lower()
        
        # Check each brand category
        for category, brands in self.protected_brands.items():
            for brand in brands:
                # Check if brand name appears in domain
                if brand in domain_lower:
                    # Check if it's the official domain
                    if brand in self.official_domains:
                        official_list = self.official_domains[brand]
                        # Check if domain matches any official domain
                        is_official = any(official in domain_lower for official in official_list)
                        if not is_official:
                            return {
                                'is_impersonation': True,
                                'brand': brand,
                                'category': category,
                                'official_domains': official_list
                            }
                    else:
                        # Brand found but no official domain mapping
                        # Check for suspicious patterns with brand name
                        # Pattern: brand-keyword.tld (e.g., sbi-verification.com)
                        suspicious_combos = [
                            f'{brand}-verification', f'{brand}-login', f'{brand}-secure',
                            f'{brand}-update', f'{brand}-kyc', f'{brand}-support',
                            f'{brand}-customer', f'{brand}-account', f'{brand}-banking',
                            f'{brand}-wallet', f'{brand}-prize', f'{brand}-claim',
                            f'{brand}-refund', f'{brand}-job', f'{brand}-offer',
                            f'{brand}-careers', f'{brand}-scholarship'
                        ]
                        
                        for combo in suspicious_combos:
                            if combo in domain_lower:
                                return {
                                    'is_impersonation': True,
                                    'brand': brand,
                                    'category': category,
                                    'official_domains': []
                                }
        
        return {
            'is_impersonation': False,
            'brand': None,
            'category': None,
            'official_domains': []
        }
    
    def get_domain_info(self, url: str) -> Dict:
        """
        Extract domain information
        Returns: {
            'domain': str,
            'subdomain': str,
            'tld': str,
            'has_port': bool,
            'port': int
        }
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # Extract port
            port = None
            has_port = ':' in domain
            if has_port:
                domain, port = domain.rsplit(':', 1)
                port = int(port)
            
            # Extract TLD and subdomain
            parts = domain.split('.')
            if len(parts) >= 2:
                tld = '.' + parts[-1]
                subdomain = '.'.join(parts[:-2]) if len(parts) > 2 else ''
            else:
                tld = ''
                subdomain = ''
            
            return {
                'domain': domain,
                'subdomain': subdomain,
                'tld': tld,
                'has_port': has_port,
                'port': port,
                'scheme': parsed.scheme
            }
            
        except Exception as e:
            print(f"Domain info extraction error: {e}")
            return {
                'domain': 'unknown',
                'subdomain': '',
                'tld': '',
                'has_port': False,
                'port': None,
                'scheme': 'unknown'
            }
