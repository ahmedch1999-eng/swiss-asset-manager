// Ensure footer hidden on login screen and center the login box
(function(){
  function initLogin(){
    var footer = document.querySelector('footer');
    if(footer) footer.style.display = 'none';
    var loginScreen = document.getElementById('passwordProtection');
    if (loginScreen) {
      loginScreen.style.display = 'flex';
      loginScreen.style.justifyContent = 'center';
      loginScreen.style.alignItems = 'center';
      loginScreen.style.width = '100vw';
      loginScreen.style.height = '100vh';
    }
  }
  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded', initLogin);
  else initLogin();
})();
