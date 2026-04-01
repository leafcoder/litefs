console.log('Litefs 静态文件示例 - JavaScript 已加载');

document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成');
    
    const links = document.querySelectorAll('a');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            console.log('点击链接:', this.href);
        });
    });
});
