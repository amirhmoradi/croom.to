// Croom Website JavaScript

(function() {
  'use strict';

  // Mobile Navigation Toggle
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');

  if (navToggle && navLinks) {
    navToggle.addEventListener('click', function() {
      navLinks.classList.toggle('active');
      navToggle.classList.toggle('active');
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(event) {
      if (!navToggle.contains(event.target) && !navLinks.contains(event.target)) {
        navLinks.classList.remove('active');
        navToggle.classList.remove('active');
      }
    });

    // Close menu when clicking a link
    navLinks.querySelectorAll('a').forEach(function(link) {
      link.addEventListener('click', function() {
        navLinks.classList.remove('active');
        navToggle.classList.remove('active');
      });
    });
  }

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href === '#') return;

      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });

  // Add scroll class to header
  const header = document.querySelector('.site-header');
  if (header) {
    let lastScroll = 0;

    window.addEventListener('scroll', function() {
      const currentScroll = window.pageYOffset;

      if (currentScroll > 50) {
        header.classList.add('scrolled');
      } else {
        header.classList.remove('scrolled');
      }

      lastScroll = currentScroll;
    });
  }

  // Copy code blocks
  document.querySelectorAll('pre code').forEach(function(codeBlock) {
    const container = codeBlock.parentNode;

    // Create copy button
    const copyButton = document.createElement('button');
    copyButton.className = 'copy-button';
    copyButton.textContent = 'Copy';
    copyButton.setAttribute('aria-label', 'Copy code to clipboard');

    copyButton.addEventListener('click', async function() {
      try {
        await navigator.clipboard.writeText(codeBlock.textContent);
        copyButton.textContent = 'Copied!';
        copyButton.classList.add('copied');

        setTimeout(function() {
          copyButton.textContent = 'Copy';
          copyButton.classList.remove('copied');
        }, 2000);
      } catch (err) {
        console.error('Failed to copy:', err);
        copyButton.textContent = 'Error';
      }
    });

    container.style.position = 'relative';
    container.appendChild(copyButton);
  });

  // Docs sidebar toggle (mobile)
  const docsSidebarToggle = document.querySelector('.docs-sidebar-toggle');
  const docsSidebar = document.querySelector('.docs-sidebar');

  if (docsSidebarToggle && docsSidebar) {
    docsSidebarToggle.addEventListener('click', function() {
      docsSidebar.classList.toggle('active');
    });
  }

  // Highlight active docs section based on scroll
  const docsContent = document.querySelector('.docs-content');
  if (docsContent) {
    const headings = docsContent.querySelectorAll('h2[id], h3[id]');
    const tocLinks = document.querySelectorAll('.docs-toc a');

    if (headings.length && tocLinks.length) {
      const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            const id = entry.target.getAttribute('id');
            tocLinks.forEach(function(link) {
              link.classList.remove('active');
              if (link.getAttribute('href') === '#' + id) {
                link.classList.add('active');
              }
            });
          }
        });
      }, {
        rootMargin: '-100px 0px -66%',
        threshold: 0
      });

      headings.forEach(function(heading) {
        observer.observe(heading);
      });
    }
  }

  // Terminal typing effect (homepage)
  const terminalCode = document.querySelector('.terminal-body code');
  if (terminalCode && window.location.pathname === '/') {
    const text = terminalCode.textContent;
    terminalCode.textContent = '';
    let i = 0;

    function typeWriter() {
      if (i < text.length) {
        terminalCode.textContent += text.charAt(i);
        i++;
        setTimeout(typeWriter, 50);
      }
    }

    // Start typing after a short delay
    setTimeout(typeWriter, 500);
  }

  // Intersection Observer for fade-in animations
  const fadeElements = document.querySelectorAll('.feature-card, .stat-card, .pricing-card');

  if (fadeElements.length && 'IntersectionObserver' in window) {
    const fadeObserver = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('fade-in');
          fadeObserver.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    fadeElements.forEach(function(el) {
      fadeObserver.observe(el);
    });
  }

})();
