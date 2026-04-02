// Litefs Fullstack Application JavaScript

(function() {
    'use strict';

    // DOM Ready
    document.addEventListener('DOMContentLoaded', function() {
        initNavigation();
        initForms();
        initAnimations();
    });

    // Navigation
    function initNavigation() {
        // 移动端菜单切换
        const navToggle = document.querySelector('.nav-toggle');
        const navLinks = document.querySelector('.nav-links');
        
        if (navToggle && navLinks) {
            navToggle.addEventListener('click', function() {
                navLinks.classList.toggle('active');
            });
        }

        // 当前页面高亮
        const currentPath = window.location.pathname;
        const navItems = document.querySelectorAll('.nav-links a');
        
        navItems.forEach(function(item) {
            if (item.getAttribute('href') === currentPath) {
                item.classList.add('active');
            }
        });
    }

    // Forms
    function initForms() {
        // 登录表单验证
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', function(e) {
                const username = document.getElementById('username').value.trim();
                const password = document.getElementById('password').value.trim();
                const errorDiv = document.getElementById('error');

                if (!username || !password) {
                    e.preventDefault();
                    errorDiv.textContent = '请输入用户名和密码';
                    return false;
                }

                errorDiv.textContent = '';
            });
        }

        // 表单输入验证
        const forms = document.querySelectorAll('form');
        forms.forEach(function(form) {
            const inputs = form.querySelectorAll('input[required], textarea[required]');
            
            inputs.forEach(function(input) {
                input.addEventListener('blur', function() {
                    validateInput(this);
                });

                input.addEventListener('input', function() {
                    if (this.classList.contains('error')) {
                        validateInput(this);
                    }
                });
            });
        });
    }

    // 验证单个输入
    function validateInput(input) {
        const value = input.value.trim();
        const formGroup = input.closest('.form-group');
        
        if (!value) {
            formGroup.classList.add('error');
            return false;
        } else {
            formGroup.classList.remove('error');
            return true;
        }
    }

    // Animations
    function initAnimations() {
        // 滚动动画
        const animatedElements = document.querySelectorAll('.post-card, .feature');
        
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, {
            threshold: 0.1
        });

        animatedElements.forEach(function(el) {
            el.classList.add('animate-ready');
            observer.observe(el);
        });
    }

    // Utility Functions
    window.LitefsApp = {
        // 显示提示信息
        showMessage: function(message, type) {
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-' + (type || 'info');
            alertDiv.textContent = message;
            
            const container = document.querySelector('main .container');
            if (container) {
                container.insertBefore(alertDiv, container.firstChild);
                
                setTimeout(function() {
                    alertDiv.remove();
                }, 5000);
            }
        },

        // AJAX 请求
        request: function(url, options) {
            options = options || {};
            
            return fetch(url, {
                method: options.method || 'GET',
                headers: Object.assign({
                    'Content-Type': 'application/json'
                }, options.headers || {}),
                body: options.body ? JSON.stringify(options.body) : null
            }).then(function(response) {
                return response.json();
            });
        },

        // 格式化日期
        formatDate: function(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('zh-CN', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
    };

})();
