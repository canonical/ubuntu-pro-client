# How to disable or re-enable APT News

APT News is a feature that allows for timely package-related news to be displayed during an `apt upgrade`. It is distinct from [Ubuntu Pro 'available update' messages](../explanations/apt_messages.md) that are also displayed during an `apt upgrade`. APT News messages are fetched from [https://motd.ubuntu.com/aptnews.json](https://motd.ubuntu.com/aptnews.json) at most once per day.

By default, APT News is turned on. In this How-to-guide, we show how to turn off and on the APT News feature for a particular machine.

## Step 1: Check the current configuration of APT News

```
pro config show apt_news
```

The default value is `True`, so if you haven't yet modified this setting, you will see:
```
apt_news True
```

## Step 2: Disable APT News

```
pro config set apt_news=false
```

This should also clear any current APT News you may be seeing on your system during `apt upgrade`.

You can double-check that the setting was successful by running the following again:

```
pro config show apt_news
```

You should now see:
```
apt_news False
```

## Step 3: (Optional) Re-enable APT News

If you change your mind and want APT News to start appearing again in `apt upgrade`, run the following:

```
pro config set apt_news=true
```

And verify the setting worked with `pro config show apt_news`.
