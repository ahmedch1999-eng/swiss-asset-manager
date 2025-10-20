// Windows Detection - Optimierte Animationen nur für Windows
(function(){
  function isWindows(){
    return navigator.userAgent && navigator.userAgent.includes('Windows');
  }
  if (isWindows()) {
    document.addEventListener('DOMContentLoaded', function(){
      document.body.classList.add('performance-mode');
      try { console.log('Windows Performance Mode aktiviert'); } catch(e){}
    });
  }
})();
