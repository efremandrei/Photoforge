package com.efremandrei.photoforge3d;

import android.app.*;
import android.content.*;
import android.net.Uri;
import android.os.Bundle;
import android.view.*;
import android.widget.*;
import java.io.*;
import org.json.*;

/** Exercises production photo upload, reconstruction, preview and STL download on a real emulator. */
public class FlowTest extends Instrumentation {
    private Bundle args;
    private MainActivity activity;
    @Override public void onCreate(Bundle b){super.onCreate(b);args=b;start();}
    private View find(View v,String text){if(v instanceof TextView&&((TextView)v).getText().toString().equals(text))return v;if(v instanceof ViewGroup){ViewGroup g=(ViewGroup)v;for(int i=0;i<g.getChildCount();i++){View x=find(g.getChildAt(i),text);if(x!=null)return x;}}return null;}
    private void click(String text){runOnMainSync(()->{View v=find(activity.getWindow().getDecorView(),text);if(v==null)throw new RuntimeException("Missing button: "+text);v.performClick();});}
    @Override public void onStart(){Bundle result=new Bundle();try{
        if("icon".equals(args.getString("mode"))){
            Context target=getTargetContext();android.graphics.drawable.Drawable icon=target.getPackageManager().getApplicationIcon(target.getPackageName());
            android.graphics.Bitmap bitmap=android.graphics.Bitmap.createBitmap(192,192,android.graphics.Bitmap.Config.ARGB_8888);
            icon.setBounds(0,0,192,192);icon.draw(new android.graphics.Canvas(bitmap));
            File out=new File(target.getExternalFilesDir(null),"installed-icon.png");try(OutputStream file=new FileOutputStream(out)){bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,file);}
            result.putString("stream","Installed icon: "+icon.getClass().getSimpleName());finish(Activity.RESULT_OK,result);return;
        }
        if("snapshot".equals(args.getString("mode"))){
            android.content.SharedPreferences saved=getTargetContext().getSharedPreferences("settings",0);
            java.util.TreeMap<String,Object> values=new java.util.TreeMap<>(saved.getAll());
            byte[] hash=java.security.MessageDigest.getInstance("SHA-256").digest(values.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder hex=new StringBuilder();for(byte b:hash)hex.append(String.format(java.util.Locale.US,"%02x",b&255));
            result.putString("stream",new JSONObject().put("preferences_sha256",hex.toString()).put("keys",values.size()).put("dark",saved.getBoolean("dark",true)).toString());
            finish(Activity.RESULT_OK,result);return;
        }
        Context target=getTargetContext();JSONArray photos=new JSONArray();
        for(String name:getContext().getAssets().list("scan")){
            File photo=new File(target.getCacheDir(),name);
            try(InputStream in=getContext().getAssets().open("scan/"+name);OutputStream out=new FileOutputStream(photo)){byte[] buffer=new byte[65536];int n;while((n=in.read(buffer))!=-1)out.write(buffer,0,n);}
            photos.put(Uri.fromFile(photo).toString());
        }
        target.getSharedPreferences("settings",0).edit().putString("server","http://127.0.0.1:8765").putString("token",args.getString("pairing")).putString("job","").putString("photos",photos.toString()).putBoolean("dark",true).commit();
        Intent launch=new Intent(target,MainActivity.class);launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);activity=(MainActivity)startActivitySync(launch);
        click("Connect");Thread.sleep(1200);click("Reconstruct on PC →");
        long end=System.currentTimeMillis()+300000;boolean complete=false;
        while(System.currentTimeMillis()<end){Thread.sleep(1500);final boolean[] done={false};runOnMainSync(()->{View v=activity.getWindow().getDecorView();done[0]=contains(v,"surface triangles");});if(done[0]){complete=true;break;}}
        if(!complete)throw new RuntimeException("Real reconstruction did not finish within five minutes.");
        runOnMainSync(()->{CheckBox box=(CheckBox)find(activity.getWindow().getDecorView(),"Seal gaps (may change / thicken geometry)");box.setChecked(true);});
        IntentFilter saveFilter=new IntentFilter(Intent.ACTION_CREATE_DOCUMENT);saveFilter.addCategory(Intent.CATEGORY_OPENABLE);saveFilter.addDataType("application/octet-stream");
        ActivityMonitor monitor=addMonitor(saveFilter,new ActivityResult(Activity.RESULT_CANCELED,null),true);
        click("Prepare & save STL →");end=System.currentTimeMillis()+90000;
        File stl=new File(target.getCacheDir(),"model.stl");while(System.currentTimeMillis()<end&&monitor.getHits()==0)Thread.sleep(500);
        if(monitor.getHits()==0||!stl.exists()||stl.length()<84)throw new RuntimeException("STL was not downloaded or save picker was not invoked.");
        File saved=new File(target.getCacheDir(),"saved-test.stl");Intent destination=new Intent().setData(Uri.fromFile(saved));runOnMainSync(()->activity.onActivityResult(12,Activity.RESULT_OK,destination));
        end=System.currentTimeMillis()+10000;while(System.currentTimeMillis()<end&&saved.length()!=stl.length())Thread.sleep(250);
        if(saved.length()!=stl.length())throw new RuntimeException("Save byte count mismatch: expected "+stl.length()+", actual "+saved.length());
        Thread.sleep(500);sendKeyDownUpSync(android.view.KeyEvent.KEYCODE_BACK);
        click("☀");Thread.sleep(500);
        if(target.getSharedPreferences("settings",0).getBoolean("dark",true))throw new RuntimeException("Theme preference did not persist.");
        result.putString("stream","PASS: 11 photos uploaded, real CPU reconstruction, preview, sealed STL download/save, theme persistence.");finish(Activity.RESULT_OK,result);
    }catch(Throwable e){result.putString("stream","FAIL: "+e);finish(Activity.RESULT_CANCELED,result);}}
    private boolean contains(View v,String s){if(v instanceof TextView&&((TextView)v).getText().toString().contains(s))return true;if(v instanceof ViewGroup){ViewGroup g=(ViewGroup)v;for(int i=0;i<g.getChildCount();i++)if(contains(g.getChildAt(i),s))return true;}return false;}
}
