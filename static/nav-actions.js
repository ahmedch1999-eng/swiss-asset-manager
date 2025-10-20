// Delegated navigation actions for landing quick links and step buttons
(function(){
  function handleClick(e){
    var el = e.target.closest('[data-nav-target]');
    if(!el) return;
    e.preventDefault();
    var page = el.getAttribute('data-nav-target');
    if(!page) return;
    var target = document.querySelector('[data-page='+CSS.escape(page)+']');
    if(target){
      target.click();
    }
  }
  document.addEventListener('click', handleClick, false);
})();
