// Croom Website JavaScript

document.addEventListener('DOMContentLoaded', function() {
  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href === '#') return;

      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        const headerOffset = 80;
        const elementPosition = target.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

        window.scrollTo({
          top: offsetPosition,
          behavior: 'smooth'
        });
      }
    });
  });

  // Add scroll class to header
  const header = document.querySelector('header');
  if (header) {
    window.addEventListener('scroll', function() {
      if (window.pageYOffset > 50) {
        header.classList.add('shadow-lg');
      } else {
        header.classList.remove('shadow-lg');
      }
    });
  }

  // Copy code blocks
  document.querySelectorAll('pre code, .font-mono').forEach(function(codeBlock) {
    if (codeBlock.closest('.bg-black\\/20, .bg-gray-900')) {
      const container = codeBlock.closest('.bg-black\\/20, .bg-gray-900, pre');
      if (!container || container.querySelector('.copy-btn')) return;

      const copyBtn = document.createElement('button');
      copyBtn.className = 'copy-btn absolute top-2 right-2 px-2 py-1 text-xs bg-white/10 hover:bg-white/20 rounded text-white/70 hover:text-white transition-colors';
      copyBtn.textContent = 'Copy';

      container.style.position = 'relative';
      container.appendChild(copyBtn);

      copyBtn.addEventListener('click', async function() {
        const text = codeBlock.textContent.replace(/^\$\s*/gm, '').replace(/^#.*\n/gm, '').trim();
        try {
          await navigator.clipboard.writeText(text);
          copyBtn.textContent = 'Copied!';
          setTimeout(() => {
            copyBtn.textContent = 'Copy';
          }, 2000);
        } catch (err) {
          console.error('Failed to copy:', err);
        }
      });
    }
  });

  // Intersection Observer for fade-in animations
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const fadeObserver = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('opacity-100', 'translate-y-0');
        entry.target.classList.remove('opacity-0', 'translate-y-4');
        fadeObserver.unobserve(entry.target);
      }
    });
  }, observerOptions);

  // Apply fade-in to sections
  document.querySelectorAll('section > div > .grid > div').forEach(function(el) {
    el.classList.add('transition-all', 'duration-500', 'opacity-0', 'translate-y-4');
    fadeObserver.observe(el);
  });
});
