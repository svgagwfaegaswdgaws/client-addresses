package edu.demo.clientaddresses;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

/** Тонкий Android-клиент: один и тот же интерфейс работает в браузере и APK. */
public class MainActivity extends Activity {
    private WebView web;
    private LinearLayout errorPanel;
    private TextView errorText;
    private ProgressBar progress;
    private SharedPreferences preferences;
    private String serverUrl;
    private boolean failed;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable timeout = () -> { web.stopLoading(); showError("Сервер долго не отвечает. Проверьте интернет и адрес подключения."); };

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        preferences = getSharedPreferences("connection", MODE_PRIVATE);
        serverUrl = preferences.getString("server", BuildConfig.DEFAULT_SERVER_URL);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(245,247,251));
        if (Build.VERSION.SDK_INT >= 30) {
            root.setOnApplyWindowInsetsListener((view, insets) -> {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars());
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
                return insets;
            });
        } else root.setFitsSystemWindows(true);
        LinearLayout bar = new LinearLayout(this);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(dp(14),dp(4),dp(8),dp(4));
        TextView title = new TextView(this);
        title.setText("Адреса клиентов"); title.setTextSize(15); title.setTextColor(Color.rgb(24,36,56));
        bar.addView(title, new LinearLayout.LayoutParams(0,dp(48),1));
        title.setGravity(Gravity.CENTER_VERTICAL);
        Button refresh = button("↻"); refresh.setContentDescription("Обновить приложение"); refresh.setOnClickListener(v -> loadServer());
        Button settings = button("Сервер"); settings.setOnClickListener(v -> settings());
        bar.addView(refresh,new LinearLayout.LayoutParams(dp(48),dp(48)));
        bar.addView(settings,new LinearLayout.LayoutParams(dp(90),dp(48)));
        root.addView(bar);
        progress = new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);
        root.addView(progress,new LinearLayout.LayoutParams(-1,dp(3)));
        errorPanel = new LinearLayout(this); errorPanel.setOrientation(LinearLayout.VERTICAL);
        errorPanel.setGravity(Gravity.CENTER); errorPanel.setPadding(dp(30),dp(30),dp(30),dp(30));
        TextView heading = new TextView(this); heading.setText("Подключение к серверу"); heading.setTextSize(22); heading.setGravity(Gravity.CENTER);
        errorText = new TextView(this); errorText.setTextSize(15); errorText.setGravity(Gravity.CENTER); errorText.setPadding(0,dp(20),0,dp(25));
        Button retry = button("Повторить"); retry.setOnClickListener(v -> loadServer());
        Button change = button("Указать адрес сервера"); change.setOnClickListener(v -> settings());
        errorPanel.addView(heading); errorPanel.addView(errorText); errorPanel.addView(retry); errorPanel.addView(change);
        root.addView(errorPanel,new LinearLayout.LayoutParams(-1,0,1));
        web = new WebView(this); web.setBackgroundColor(Color.rgb(245,247,251));
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(false);
        web.getSettings().setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        web.setWebChromeClient(new WebChromeClient() {
            @Override public void onProgressChanged(WebView view,int value) { progress.setProgress(value); }
        });
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request) {
                Uri target=request.getUrl(), base=Uri.parse(serverUrl);
                if (!"http".equals(target.getScheme()) && !"https".equals(target.getScheme())) return true;
                if (target.getScheme().equals(base.getScheme()) && target.getAuthority().equals(base.getAuthority())) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW,target)); } catch (Exception ignored) { }
                return true;
            }
            @Override public void onPageStarted(WebView view,String url,android.graphics.Bitmap icon) { progress.setVisibility(View.VISIBLE); }
            @Override public void onPageFinished(WebView view,String url) {
                handler.removeCallbacks(timeout); progress.setVisibility(View.GONE);
                if (!failed) { web.setVisibility(View.VISIBLE); errorPanel.setVisibility(View.GONE); }
            }
            @Override public void onReceivedError(WebView view,WebResourceRequest request,WebResourceError error) {
                if (request.isForMainFrame()) showError("Не удалось открыть приложение. Проверьте интернет и правильность адреса сервера.");
            }
            @Override public void onReceivedHttpError(WebView view,WebResourceRequest request,WebResourceResponse response) {
                if(request.isForMainFrame()) showError("Сервер вернул ошибку " + response.getStatusCode() + ". Проверьте, что приложение размещено и работает.");
            }
        });
        root.addView(web,new LinearLayout.LayoutParams(-1,0,1));
        setContentView(root);
        loadServer();
    }

    private int dp(int n) { return (int)(n*getResources().getDisplayMetrics().density+.5f); }
    private Button button(String text) { Button b=new Button(this); b.setText(text); b.setAllCaps(false); b.setTextSize(13); return b; }
    private void showError(String message) {
        failed=true; handler.removeCallbacks(timeout); progress.setVisibility(View.GONE);
        web.setVisibility(View.GONE); errorPanel.setVisibility(View.VISIBLE); errorText.setText(message);
    }
    private void loadServer() {
        handler.removeCallbacks(timeout);
        if (serverUrl==null || serverUrl.isEmpty()) { showError("Укажите адрес опубликованного приложения кнопкой «Сервер». Пример: https://yourname.pythonanywhere.com"); return; }
        failed=false; errorPanel.setVisibility(View.GONE); web.setVisibility(View.VISIBLE);
        progress.setVisibility(View.VISIBLE); web.loadUrl(serverUrl); handler.postDelayed(timeout,20000);
    }
    private void settings() {
        final EditText input = new EditText(this);
        input.setSingleLine(true); input.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        input.setHint("https://yourname.pythonanywhere.com"); input.setText(serverUrl);
        LinearLayout box=new LinearLayout(this); box.setOrientation(LinearLayout.VERTICAL); box.setPadding(dp(24),dp(8),dp(24),0);
        TextView help=new TextView(this); help.setText("Адрес сервера с приложением. Для телефона и компьютера в одной Wi-Fi сети можно указать http://IP-компьютера:8000. localhost на телефоне означает сам телефон.");
        box.addView(help); box.addView(input,new LinearLayout.LayoutParams(-1,dp(64)));
        AlertDialog dialog = new AlertDialog.Builder(this).setTitle("Адрес сервера").setView(box).setNegativeButton("Отмена",null).setPositiveButton("Подключиться",null).create();
        dialog.setOnShowListener(v -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(button -> {
            String raw=input.getText().toString().trim(); Uri uri=Uri.parse(raw);
            if ((!"https".equals(uri.getScheme()) && !"http".equals(uri.getScheme())) || uri.getHost()==null || uri.getUserInfo()!=null || uri.getQuery()!=null || uri.getFragment()!=null || (uri.getPath()!=null && !uri.getPath().isEmpty() && !"/".equals(uri.getPath()))) {
                input.setError("Укажите полный адрес: https://имя-сервера, без пути и параметров"); return;
            }
            serverUrl=raw.replaceAll("/+$","")+"/";
            preferences.edit().putString("server",serverUrl).apply(); web.clearHistory(); dialog.dismiss(); loadServer();
        }));
        dialog.show();
    }
    @Override public void onBackPressed() { if(web.canGoBack()) web.goBack(); else super.onBackPressed(); }
    @Override protected void onDestroy() { handler.removeCallbacksAndMessages(null); web.destroy(); super.onDestroy(); }
}
